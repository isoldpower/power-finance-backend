from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from redis.asyncio import Redis

from data_read_core.shared.metrics import MoneyFolder, metrics_version
from data_read_core.shared.postgres_orm import AccountGroups
from data_read_core.shared.query_results import FetchedResource

from .cache_worker import CacheWorker
from .dtos import (
    BalanceSheetDTO,
    CashFlowDTO,
    GetMetricsQuery,
    MetricsDTO,
    NetWorthDTO,
    Section,
    SeriesPointDTO,
)
from .infra import (
    BucketedTotals,
    GroupSubtotals,
    TransactionAggregate,
    aggregate_transactions,
    count_unbalanced_dispatches,
    earliest_transaction_at,
    get_redis_client,
    sum_accounts_by_group_and_currency,
    sum_by_bucket,
)
from .logger_shortcuts import (
    log_served_from_cache,
    log_served_from_store,
)


@dataclass(frozen=True)
class SeriesWindow:
    bucketed: BucketedTotals
    since: datetime
    until: datetime

    @property
    def currencies(self) -> list[str]:
        return [currency for by_currency in self.bucketed.values() for currency in by_currency]


class GetMetricsQueryHandler:
    def __init__(
        self,
        redis_client: Redis | None = None,
        folder: MoneyFolder | None = None,
        now: datetime | None = None,
    ):
        redis_client = redis_client or get_redis_client()

        self._redis_client = redis_client
        self._cache_worker = CacheWorker(redis_client)
        self._folder = folder
        self._now = now

    async def handle(self, query: GetMetricsQuery) -> FetchedResource:
        version = await metrics_version(query.user_id)
        cached_value = await self._cache_worker.try_serve_from_cache(
            query,
            version,
        )
        if cached_value is not None:
            log_served_from_cache(
                query.user_id,
                query.section_signature,
            )
            return FetchedResource(
                resource=cached_value,
                cached=True,
            )

        metrics = await self._build(query)
        await self._cache_worker.save_to_cache(
            query,
            version,
            metrics,
        )

        log_served_from_store(
            query.user_id,
            query.section_signature,
        )
        return FetchedResource(
            resource=metrics,
            cached=False,
        )

    async def _build(self, query: GetMetricsQuery) -> MetricsDTO:
        wants_net_worth = query.wants(Section.NET_WORTH)
        wants_cash_flow = query.wants(Section.CASH_FLOW)

        aggregate = await aggregate_transactions(
            query.user_id,
            query.window.since,
            needs_window_total=wants_net_worth,
            needs_flows=wants_cash_flow,
        )
        accounts_chart = (
            await sum_accounts_by_group_and_currency(query.user_id)
            if query.wants(Section.BALANCE)
            else {}
        )
        series_window = await self._series_window(query) if wants_net_worth else None

        money_folder = self._folder or MoneyFolder(query.currency)
        await money_folder.prepare(
            [
                *aggregate.currencies,
                *_currencies_in(accounts_chart),
                *(series_window.currencies if series_window else []),
            ]
        )

        return MetricsDTO(
            currency=query.currency,
            balance=await self._calculate_balance(query, accounts_chart, money_folder),
            net_worth=await self._net_worth(aggregate, series_window, money_folder, query.points)
            if series_window
            else None,
            cash_flow=(
                CashFlowDTO(
                    inflow=await money_folder.fold(aggregate.window_inflow),
                    outflow=await money_folder.fold(aggregate.window_outflow),
                )
                if wants_cash_flow
                else None
            ),
        )

    async def _series_window(self, query: GetMetricsQuery) -> SeriesWindow:
        time_until = self._now or datetime.now(UTC)
        time_since = (
            query.window.since or await earliest_transaction_at(query.user_id) or time_until
        )

        return SeriesWindow(
            bucketed=await sum_by_bucket(
                query.user_id,
                time_since,
                time_until,
                query.points,
            ),
            since=time_since,
            until=time_until,
        )

    async def _calculate_balance(
        self,
        query: GetMetricsQuery,
        group_chart: GroupSubtotals,
        money_folder: MoneyFolder,
    ) -> BalanceSheetDTO | None:
        if not query.wants(Section.BALANCE):
            return None

        return BalanceSheetDTO(
            assets=await money_folder.fold(
                group_chart.get(
                    AccountGroups.ASSETS,
                    {},
                )
            ),
            liabilities=await money_folder.fold(
                group_chart.get(
                    AccountGroups.LIABILITIES,
                    {},
                )
            ),
            equity=await money_folder.fold(
                group_chart.get(
                    AccountGroups.EQUITY,
                    {},
                )
            ),
            unbalanced_dispatches=await count_unbalanced_dispatches(query.user_id),
        )

    async def _net_worth(
        self,
        aggregate: TransactionAggregate,
        series_window: SeriesWindow,
        folder: MoneyFolder,
        chart_points: int,
    ) -> NetWorthDTO:
        opening_balance = await folder.fold(aggregate.before)
        total_balance = opening_balance + await folder.fold(aggregate.window_total)

        return NetWorthDTO(
            total_amount=total_balance,
            opening_balance=opening_balance,
            points_series=await self._series(
                series_window,
                folder,
                opening_balance,
                chart_points,
            ),
        )

    async def _series(
        self,
        window: SeriesWindow,
        folder: MoneyFolder,
        opening: Decimal,
        points: int,
    ) -> list[SeriesPointDTO]:
        window_width = (window.until - window.since) / points
        running_amount = opening
        points_series: list[SeriesPointDTO] = []

        for index in range(points):
            running_amount += await folder.fold(window.bucketed.get(index, {}))
            points_series.append(
                SeriesPointDTO(
                    timestamp=window.since + window_width * (index + 1),
                    amount=running_amount,
                )
            )

        return points_series


def _currencies_in(chart: GroupSubtotals) -> list[str]:
    return [currency for by_currency in chart.values() for currency in by_currency]

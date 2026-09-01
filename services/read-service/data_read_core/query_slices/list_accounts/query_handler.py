import asyncio
from decimal import ROUND_HALF_UP, Decimal

from redis.asyncio import Redis

from data_read_core.shared.exchange_rates import ExchangeRateService, get_rate_service

from .cache_worker import CacheWorker
from .dtos import (
    AccountDTO,
    CacheOperationData,
    ChartFilters,
    FetchedChart,
    ListAccountsQuery,
)
from .infra import (
    Thresholds,
    count_accounts_by_group,
    count_owned_accounts,
    distinct_account_currencies,
    fetch_owned_accounts,
    get_redis_client,
)
from .logger_shortcuts import (
    log_served_from_cache,
    log_served_from_store,
)

BOOK_EXPONENT = Decimal("0.01")


class ListAccountsQueryHandler:
    def __init__(
        self,
        redis_client: Redis | None = None,
        rate_service: ExchangeRateService | None = None,
    ):
        redis_client = redis_client or get_redis_client()

        self._redis_client = redis_client
        self._cache_worker = CacheWorker(redis_client)
        self._rate_service = rate_service

    async def handle(self, query: ListAccountsQuery) -> FetchedChart:
        cache_operation = self._build_cache_operation(query)
        cached_value = await self._cache_worker.try_serve_from_cache(cache_operation)
        if cached_value is not None:
            accounts, total, groups = cached_value
            log_served_from_cache(query.user_id)
            return FetchedChart(rows=accounts, total=total, groups=groups, cached=True)

        accounts, total, groups = await self._make_store_request(query)
        await self._cache_worker.save_to_cache(
            context=cache_operation,
            accounts=accounts,
            total=total,
            groups=groups,
        )

        log_served_from_store(query.user_id, accounts, total)
        return FetchedChart(rows=accounts, total=total, groups=groups, cached=False)

    async def _make_store_request(
        self,
        query: ListAccountsQuery,
    ) -> tuple[list[AccountDTO], int, dict[str, int]]:
        thresholds = await self._resolve_thresholds(query.user_id, query.filters)
        total, rows, groups = await asyncio.gather(
            count_owned_accounts(query.user_id, query.filters, thresholds),
            fetch_owned_accounts(query.user_id, query.page, query.filters, thresholds),
            count_accounts_by_group(query.user_id, query.filters, thresholds),
        )

        return [AccountDTO.from_read_model(row) for row in rows], total, groups

    async def _resolve_thresholds(
        self,
        user_id: int,
        filters: ChartFilters,
    ) -> Thresholds | None:
        """`lowbar` arrives in the caller's currency; balances are held in each
        account's book currency. Convert the threshold once per book currency
        rather than converting every balance, which no index could then serve."""

        if not filters.narrows_by_balance:
            return None

        return {
            currency_code: await self._converted(filters.lowbar, filters.currency, currency_code)
            for currency_code in await distinct_account_currencies(user_id)
        }

    async def _converted(self, amount: Decimal, from_code: str, to_code: str) -> Decimal:
        if from_code == to_code:
            return amount

        rate, _ = await self._rates().rate_between(from_code, to_code)

        return (amount * rate).quantize(BOOK_EXPONENT, rounding=ROUND_HALF_UP)

    def _rates(self) -> ExchangeRateService:
        """Resolved on demand: the overwhelming majority of chart requests set
        no threshold, and those have no business reaching for a rate feed."""

        return self._rate_service or get_rate_service()

    def _build_cache_operation(self, query: ListAccountsQuery) -> CacheOperationData:
        return CacheOperationData(
            user_id=query.user_id,
            filters=query.filters.as_cache_material(),
            limit=query.page.limit,
            cursor=query.page.cache_token,
        )

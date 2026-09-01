import json
from datetime import datetime
from decimal import Decimal

from redis.asyncio import Redis

from .dtos import (
    BalanceSheetDTO,
    CashFlowDTO,
    GetMetricsQuery,
    MetricsDTO,
    NetWorthDTO,
    SeriesPointDTO,
)
from .infra import CACHE_TTL_SECONDS, get_metrics_cache_key


class CacheWorker:
    def __init__(self, redis_client: Redis) -> None:
        self._redis_client = redis_client

    async def try_serve_from_cache(
        self,
        query: GetMetricsQuery,
        version: str,
    ) -> MetricsDTO | None:
        cached_value = await self._redis_client.get(_key_for(query, version))
        if cached_value is None:
            return None

        raw = json.loads(cached_value)

        return MetricsDTO(
            currency=raw["currency"],
            balance=_balance_from(raw.get("balance")),
            net_worth=_net_worth_from(raw.get("net_worth")),
            cash_flow=_cash_flow_from(raw.get("cash_flow")),
        )

    async def save_to_cache(
        self,
        query: GetMetricsQuery,
        version: str,
        metrics: MetricsDTO,
    ) -> None:
        await self._redis_client.set(
            _key_for(query, version),
            json.dumps(
                {
                    "currency": metrics.currency,
                    "balance": _balance_to(metrics.balance),
                    "net_worth": _net_worth_to(metrics.net_worth),
                    "cash_flow": _cash_flow_to(metrics.cash_flow),
                }
            ),
            ex=CACHE_TTL_SECONDS,
        )


def _key_for(query: GetMetricsQuery, version: str) -> str:
    return get_metrics_cache_key(
        user_id=query.user_id,
        version=version,
        currency=query.currency,
        since=query.window.cache_signature,
        points=query.points,
        sections=query.section_signature,
    )


def _balance_to(balance_sheet: BalanceSheetDTO | None) -> dict | None:
    if balance_sheet is None:
        return None

    return {
        "assets": str(balance_sheet.assets),
        "liabilities": str(balance_sheet.liabilities),
        "equity": str(balance_sheet.equity),
        "unbalanced_dispatches": balance_sheet.unbalanced_dispatches,
    }


def _balance_from(raw_dictionary: dict | None) -> BalanceSheetDTO | None:
    if raw_dictionary is None:
        return None

    return BalanceSheetDTO(
        assets=Decimal(raw_dictionary["assets"]),
        liabilities=Decimal(raw_dictionary["liabilities"]),
        equity=Decimal(raw_dictionary["equity"]),
        unbalanced_dispatches=raw_dictionary["unbalanced_dispatches"],
    )


def _net_worth_to(net_worth: NetWorthDTO | None) -> dict | None:
    if net_worth is None:
        return None

    return {
        "total": str(net_worth.total_amount),
        "opening": str(net_worth.opening_balance),
        "series": [
            {
                "timestamp": point.timestamp.isoformat(),
                "amount": str(point.amount),
            }
            for point in net_worth.points_series
        ],
    }


def _net_worth_from(raw_dictionary: dict | None) -> NetWorthDTO | None:
    if raw_dictionary is None:
        return None

    return NetWorthDTO(
        total_amount=Decimal(raw_dictionary["total"]),
        opening_balance=Decimal(raw_dictionary["opening"]),
        points_series=[
            SeriesPointDTO(
                timestamp=datetime.fromisoformat(point["timestamp"]),
                amount=Decimal(point["amount"]),
            )
            for point in raw_dictionary["series"]
        ],
    )


def _cash_flow_to(cash_flow: CashFlowDTO | None) -> dict | None:
    if cash_flow is None:
        return None

    return {
        "inflow": str(cash_flow.inflow),
        "outflow": str(cash_flow.outflow),
    }


def _cash_flow_from(raw_dictionary: dict | None) -> CashFlowDTO | None:
    if raw_dictionary is None:
        return None

    return CashFlowDTO(
        inflow=Decimal(raw_dictionary["inflow"]),
        outflow=Decimal(raw_dictionary["outflow"]),
    )

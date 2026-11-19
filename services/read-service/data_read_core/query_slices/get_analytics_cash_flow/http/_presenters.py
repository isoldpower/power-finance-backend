from data_read_core.shared.analytics import AnalyticsScope, Granularity, present_scope_meta
from data_read_core.shared.money import money_at_scale
from data_read_core.shared.timestamps import to_iso

from ..dtos import CashFlowBucketDTO, CashFlowDTO


async def present_cash_flow(cash_flow: CashFlowDTO, currency: str) -> dict:
    return {
        "buckets": [await _present_bucket(bucket, currency) for bucket in cash_flow.buckets],
        "totals": {
            "inflow": await money_at_scale(cash_flow.inflow, currency),
            "outflow": await money_at_scale(cash_flow.outflow, currency),
            "net": await money_at_scale(cash_flow.net, currency),
        },
    }


def present_meta(scope: AnalyticsScope, granularity: Granularity, cached: bool) -> dict:
    return present_scope_meta(scope, cached, granularity=granularity.value)


async def _present_bucket(bucket: CashFlowBucketDTO, currency: str) -> dict:
    return {
        "start": to_iso(bucket.start),
        "end": to_iso(bucket.end),
        "inflow": await money_at_scale(bucket.inflow, currency),
        "outflow": await money_at_scale(bucket.outflow, currency),
        "net": await money_at_scale(bucket.net, currency),
        "transactions_count": bucket.transactions_count,
        "closing_balance": await money_at_scale(bucket.closing_balance, currency),
    }

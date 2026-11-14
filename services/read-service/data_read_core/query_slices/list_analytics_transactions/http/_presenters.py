from data_read_core.shared.analytics import (
    AnalyticsScope,
    present_collection_meta,
    present_transaction_brief,
)
from data_read_core.shared.money import money_at_scale

from ..dtos import AnalyticsTransactionsDTO


async def present_transactions(transactions: AnalyticsTransactionsDTO, currency: str) -> list[dict]:
    return [
        await present_transaction_brief(transaction, currency)
        for transaction in transactions.transactions
    ]


async def present_meta(
    scope: AnalyticsScope,
    transactions: AnalyticsTransactionsDTO,
    limit: int,
    cached: bool,
) -> dict:
    return present_collection_meta(
        scope,
        cached,
        limit=limit,
        total=transactions.total,
        total_inflow=await money_at_scale(transactions.total_inflow, scope.currency),
        total_outflow=await money_at_scale(transactions.total_outflow, scope.currency),
    )

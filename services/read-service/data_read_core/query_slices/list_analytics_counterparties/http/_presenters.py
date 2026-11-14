from data_read_core.shared.analytics import AnalyticsScope, as_percentage, present_collection_meta
from data_read_core.shared.money import money_at_scale
from data_read_core.shared.timestamps import to_iso

from ..dtos import CounterpartiesDTO, CounterpartyDTO


async def present_counterparties(counterparties: CounterpartiesDTO, currency: str) -> list[dict]:
    return [
        await _present_counterparty(counterparty, currency)
        for counterparty in counterparties.counterparties
    ]


def present_meta(
    scope: AnalyticsScope,
    counterparties: CounterpartiesDTO,
    limit: int,
    cached: bool,
) -> dict:
    return present_collection_meta(
        scope,
        cached,
        limit=limit,
        total=counterparties.total_counterparties,
        total_counterparties=counterparties.total_counterparties,
    )


async def _present_counterparty(counterparty: CounterpartyDTO, currency: str) -> dict:
    return {
        "name": counterparty.name,
        "category": counterparty.category,
        "amount": await money_at_scale(counterparty.amount, currency),
        "share": as_percentage(counterparty.share),
        "transactions_count": counterparty.transactions_count,
        "average": await money_at_scale(counterparty.average, currency),
        "last_seen_at": to_iso(counterparty.last_seen_at),
    }

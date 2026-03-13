from dataclasses import dataclass

from finances.infrastructure.selectors import DjangoTransactionSelectorsCollection

from ..dtos import SpendingHeatmapResultDTO
from ..interfaces import TransactionSelectorsCollection


@dataclass
class GetSpendingHeatmapQuery:
    user_id: int

class GetSpendingHeatmapQueryHandler:
    transaction_selectors: TransactionSelectorsCollection

    def __init__(
        self,
        transaction_selectors: TransactionSelectorsCollection | None = None,
    ) -> None:
        self.transaction_selectors = transaction_selectors or DjangoTransactionSelectorsCollection()

    def handle(self, query: GetSpendingHeatmapQuery) -> SpendingHeatmapResultDTO:
        rows = self.transaction_selectors.get_daily_spending(user_id=query.user_id)
        data = {
            item["day"].isoformat(): float(item["total"] or 0)
            for item in rows if item["day"] is not None
        }

        return SpendingHeatmapResultDTO(spending_by_day=data)

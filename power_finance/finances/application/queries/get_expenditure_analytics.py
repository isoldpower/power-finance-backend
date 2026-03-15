from dataclasses import dataclass

from finances.infrastructure.selectors import DjangoTransactionSelectorsCollection

from ..interfaces import TransactionSelectorsCollection
from ..dtos import ExpenditureAnalyticsResultDTO


@dataclass(frozen=True)
class GetExpenditureAnalyticsQuery:
    user_id: int


class GetExpenditureAnalyticsQueryHandler:
    transaction_selector: TransactionSelectorsCollection

    def __init__(
        self,
        selector: TransactionSelectorsCollection | None = None
    ) -> None:
        self.transaction_selector = selector or DjangoTransactionSelectorsCollection()

    def handle(self, query: GetExpenditureAnalyticsQuery) -> ExpenditureAnalyticsResultDTO:
        rows = self.transaction_selector.get_monthly_expenditure_and_income(
            user_id=query.user_id
        )
        data = {
            item["month"].isoformat(): {
                "income": float(item["income"] or 0),
                "expenses": float(item["expenses"] or 0)
            } for item in rows if item["month"] is not None
        }

        return ExpenditureAnalyticsResultDTO(expenditure_by_month=data)

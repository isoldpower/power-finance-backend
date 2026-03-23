from dataclasses import dataclass

from finances.infrastructure.selectors import DjangoTransactionSelectorsCollection

from ...interfaces import TransactionSelectorsCollection
from ...dtos import CategoryAnalyticsItemDTO, CategoryAnalyticsResultDTO


@dataclass(frozen=True)
class GetCategoriesAnalyticsQuery:
    user_id: int


class GetCategoriesAnalyticsQueryHandler:
    categories_selector: TransactionSelectorsCollection

    def __init__(
        self,
        categories_selector: TransactionSelectorsCollection | None = None
    ) -> None:
        self.categories_selector = categories_selector or DjangoTransactionSelectorsCollection()

    def handle(self, query: GetCategoriesAnalyticsQuery) -> CategoryAnalyticsResultDTO:
        rows = self.categories_selector.get_expenses_by_category(user_id=query.user_id)
        items = [CategoryAnalyticsItemDTO(
            category=row["category"],
            amount=float(row["amount"] or 0)
        ) for row in rows]

        return CategoryAnalyticsResultDTO(items=items)

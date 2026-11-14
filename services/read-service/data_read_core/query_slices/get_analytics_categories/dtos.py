from dataclasses import dataclass
from decimal import Decimal

from data_read_core.shared.analytics import AnalyticsScope, LedgerSide


@dataclass(frozen=True)
class GetAnalyticsCategoriesQuery:
    scope: AnalyticsScope
    side: LedgerSide

    @property
    def user_id(self) -> int:
        return self.scope.user_id

    @property
    def cache_signature(self) -> dict:
        return {**self.scope.cache_signature, "type": self.side.value}


@dataclass(frozen=True)
class CategoryShareDTO:
    category: str | None
    amount: Decimal
    share: Decimal
    transactions_count: int
    previous_amount: Decimal
    change_percentage: Decimal | None

    @property
    def average(self) -> Decimal:
        return self.amount / self.transactions_count


@dataclass(frozen=True)
class CategoriesDTO:
    side: LedgerSide
    total: Decimal
    categories: list[CategoryShareDTO]

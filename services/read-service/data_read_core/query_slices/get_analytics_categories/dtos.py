from dataclasses import dataclass
from decimal import Decimal

from data_read_core.shared.analytics import (
    AnalyticsCategory,
    LedgerSide,
    ScopedAnalyticsQuery,
)


@dataclass(frozen=True)
class GetAnalyticsCategoriesQuery(ScopedAnalyticsQuery):
    side: LedgerSide

    @property
    def report_parameters(self) -> dict:
        return {"type": self.side.value}


@dataclass(frozen=True)
class CategoryShareDTO:
    category: AnalyticsCategory | None
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

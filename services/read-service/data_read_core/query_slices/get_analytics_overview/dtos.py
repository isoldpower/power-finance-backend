from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from data_read_core.shared.analytics import AnalyticsScope, TransactionBriefDTO


@dataclass(frozen=True)
class GetAnalyticsOverviewQuery:
    scope: AnalyticsScope

    @property
    def user_id(self) -> int:
        return self.scope.user_id

    @property
    def cache_signature(self) -> dict:
        return self.scope.cache_signature


@dataclass(frozen=True)
class TopCategoryDTO:
    category: str | None
    amount: Decimal
    share: Decimal


@dataclass(frozen=True)
class PeriodSummaryDTO:
    since: datetime
    until: datetime
    inflow: Decimal
    outflow: Decimal
    savings_rate: Decimal | None
    transactions_count: int
    active_days: int
    average_daily_outflow: Decimal
    largest_expense: TransactionBriefDTO | None
    largest_income: TransactionBriefDTO | None
    top_expense_category: TopCategoryDTO | None

    @property
    def net(self) -> Decimal:
        return self.inflow - self.outflow


@dataclass(frozen=True)
class OverviewDTO:
    current: PeriodSummaryDTO
    previous: PeriodSummaryDTO

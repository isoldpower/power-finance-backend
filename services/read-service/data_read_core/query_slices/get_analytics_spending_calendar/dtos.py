from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from data_read_core.shared.analytics import AnalyticsScope


@dataclass(frozen=True)
class GetAnalyticsSpendingCalendarQuery:
    scope: AnalyticsScope

    @property
    def user_id(self) -> int:
        return self.scope.user_id

    @property
    def cache_signature(self) -> dict:
        return self.scope.cache_signature


@dataclass(frozen=True)
class CalendarDayDTO:
    local_date: date
    inflow: Decimal
    outflow: Decimal
    transactions_count: int

    @property
    def net(self) -> Decimal:
        return self.inflow - self.outflow


@dataclass(frozen=True)
class SpendingCalendarDTO:
    days: list[CalendarDayDTO]

    @property
    def peak_outflow(self) -> Decimal:
        return max((day.outflow for day in self.days), default=Decimal(0))

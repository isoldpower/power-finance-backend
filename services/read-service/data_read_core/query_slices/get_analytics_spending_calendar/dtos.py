from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from data_read_core.shared.analytics import ZERO, ScopedAnalyticsQuery


@dataclass(frozen=True)
class GetAnalyticsSpendingCalendarQuery(ScopedAnalyticsQuery):
    pass


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
        return max((day.outflow for day in self.days), default=ZERO)

from data_read_core.shared.analytics import AnalyticsScope, present_scope_meta
from data_read_core.shared.money import money_at_scale

from ..dtos import CalendarDayDTO, SpendingCalendarDTO


async def present_spending_calendar(calendar: SpendingCalendarDTO, currency: str) -> dict:
    return {
        "days": [await _present_day(day, currency) for day in calendar.days],
        "peak_outflow": await money_at_scale(calendar.peak_outflow, currency),
    }


def present_meta(scope: AnalyticsScope, cached: bool) -> dict:
    return present_scope_meta(scope, cached)


async def _present_day(day: CalendarDayDTO, currency: str) -> dict:
    return {
        "date": day.local_date.isoformat(),
        "inflow": await money_at_scale(day.inflow, currency),
        "outflow": await money_at_scale(day.outflow, currency),
        "net": await money_at_scale(day.net, currency),
        "transactions_count": day.transactions_count,
    }

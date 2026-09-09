from datetime import UTC, datetime, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

DAY = timedelta(days=1)


class Period(StrEnum):
    LAST_WEEK = "last_week"
    LAST_MONTH = "last_month"
    LAST_YEAR = "last_year"
    ALL_TIME = "all_time"


DEFAULT_PERIOD = Period.LAST_MONTH

ROLLING_DAYS: dict[Period, int] = {
    Period.LAST_WEEK: 7,
    Period.LAST_MONTH: 30,
    Period.LAST_YEAR: 365,
}


def period_bounds(
    period: Period,
    zone: ZoneInfo,
    now: datetime | None = None,
) -> tuple[datetime | None, datetime | None]:
    if period is Period.ALL_TIME:
        return None, None

    local_now = (now or datetime.now(UTC)).astimezone(zone)
    midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)

    window_end = midnight + DAY
    window_start = window_end - timedelta(days=ROLLING_DAYS[period])

    return (
        window_start.astimezone(UTC),
        window_end.astimezone(UTC),
    )

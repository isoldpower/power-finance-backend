from datetime import UTC, datetime, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

DAY = timedelta(days=1)
WEEK = timedelta(days=7)


class Period(StrEnum):
    LAST_WEEK = "last_week"
    LAST_MONTH = "last_month"
    LAST_YEAR = "last_year"
    ALL_TIME = "all_time"


DEFAULT_PERIOD = Period.LAST_MONTH


def period_bounds(
    period: Period,
    zone: ZoneInfo,
    now: datetime | None = None,
) -> tuple[datetime | None, datetime | None]:
    if period is Period.ALL_TIME:
        return None, None

    local_now = (now or datetime.now(UTC)).astimezone(zone)
    midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period is Period.LAST_WEEK:
        current_start = midnight - timedelta(days=midnight.weekday())
        previous_start = current_start - WEEK
    elif period is Period.LAST_MONTH:
        current_start = midnight.replace(day=1)
        previous_start = (current_start - DAY).replace(day=1)
    else:
        current_start = midnight.replace(month=1, day=1)
        previous_start = current_start.replace(year=current_start.year - 1)

    return previous_start.astimezone(UTC), current_start.astimezone(UTC)

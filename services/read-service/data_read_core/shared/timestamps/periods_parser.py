from datetime import UTC, datetime, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

DAY = timedelta(days=1)
WEEK = timedelta(days=7)


class Period(StrEnum):
    """The reporting windows a wallet can be asked for.

    Every one of them is a CALENDAR window resolved in the caller's timezone,
    not a rolling count of days: `last_month` on the 3rd means the whole of the
    previous month, not the 30 days before now. Two clients in different zones
    can therefore straddle a boundary and see different figures for the same
    wallet, which is the point of resolving them server-side at all.
    """

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
    """The period as a UTC half-open range, or (None, None) for all time.

    Half-open on purpose: the end of one window is the start of the next, so
    consecutive periods tile without double-counting the instant between them.
    `all_time` returns no bounds at all rather than a very old epoch, so callers
    drop the filter instead of widening it.
    """

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

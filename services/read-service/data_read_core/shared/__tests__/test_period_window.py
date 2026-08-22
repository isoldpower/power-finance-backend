from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from data_read_core.shared.timestamps import Period, period_bounds

WARSAW = ZoneInfo("Europe/Warsaw")
CHICAGO = ZoneInfo("America/Chicago")
UTC_ZONE = ZoneInfo("UTC")


def test_returns_the_previous_whole_calendar_month():
    since, until = period_bounds(Period.LAST_MONTH, UTC_ZONE, datetime(2026, 8, 21, 12, tzinfo=UTC))

    assert since == datetime(2026, 7, 1, tzinfo=UTC)
    assert until == datetime(2026, 8, 1, tzinfo=UTC)


def test_window_is_stable_anywhere_inside_the_current_month():
    early = period_bounds(Period.LAST_MONTH, UTC_ZONE, datetime(2026, 8, 1, 0, 0, tzinfo=UTC))
    late = period_bounds(Period.LAST_MONTH, UTC_ZONE, datetime(2026, 8, 31, 23, 59, tzinfo=UTC))

    assert early == late


def test_january_rolls_back_into_the_previous_year():
    since, until = period_bounds(Period.LAST_MONTH, UTC_ZONE, datetime(2026, 1, 15, tzinfo=UTC))

    assert since == datetime(2025, 12, 1, tzinfo=UTC)
    assert until == datetime(2026, 1, 1, tzinfo=UTC)


def test_boundaries_are_local_midnight_not_utc_midnight():
    since, until = period_bounds(Period.LAST_MONTH, WARSAW, datetime(2026, 8, 21, 12, tzinfo=UTC))

    assert since == datetime(2026, 6, 30, 22, tzinfo=UTC)
    assert until == datetime(2026, 7, 31, 22, tzinfo=UTC)


def test_two_zones_straddling_a_month_boundary_see_different_months():
    """The first of the month in Warsaw is still the last of the previous month
    in Chicago, so the two ask for windows a month apart. That is the point."""

    instant = datetime(2026, 8, 1, 3, tzinfo=UTC)

    warsaw_since, _ = period_bounds(Period.LAST_MONTH, WARSAW, instant)
    chicago_since, _ = period_bounds(Period.LAST_MONTH, CHICAGO, instant)

    assert warsaw_since.astimezone(WARSAW).month == 7
    assert chicago_since.astimezone(CHICAGO).month == 6


def test_defaults_to_now_when_no_instant_is_given():
    since, until = period_bounds(Period.LAST_MONTH, UTC_ZONE)

    assert since < until
    assert since.tzinfo is not None


def test_last_week_is_the_previous_whole_iso_week():
    """Monday-to-Monday, not the seven days before now."""

    # 2026-08-21 is a Friday; the week before it runs Mon 10th to Mon 17th.
    since, until = period_bounds(Period.LAST_WEEK, UTC_ZONE, datetime(2026, 8, 21, tzinfo=UTC))

    assert since == datetime(2026, 8, 10, tzinfo=UTC)
    assert until == datetime(2026, 8, 17, tzinfo=UTC)


def test_last_week_is_stable_all_week():
    monday = period_bounds(Period.LAST_WEEK, UTC_ZONE, datetime(2026, 8, 17, tzinfo=UTC))
    sunday = period_bounds(Period.LAST_WEEK, UTC_ZONE, datetime(2026, 8, 23, 23, tzinfo=UTC))

    assert monday == sunday


def test_last_year_is_the_previous_whole_calendar_year():
    since, until = period_bounds(Period.LAST_YEAR, UTC_ZONE, datetime(2026, 8, 21, tzinfo=UTC))

    assert since == datetime(2025, 1, 1, tzinfo=UTC)
    assert until == datetime(2026, 1, 1, tzinfo=UTC)


def test_all_time_has_no_bounds():
    """Not a very old epoch — genuinely unbounded, so the caller's filter is
    dropped rather than widened."""

    assert period_bounds(Period.ALL_TIME, UTC_ZONE) == (None, None)


def test_every_period_resolves_in_the_callers_zone():
    for period in (Period.LAST_WEEK, Period.LAST_MONTH, Period.LAST_YEAR):
        warsaw, _ = period_bounds(period, WARSAW, datetime(2026, 8, 21, 12, tzinfo=UTC))
        utc, _ = period_bounds(period, UTC_ZONE, datetime(2026, 8, 21, 12, tzinfo=UTC))

        assert warsaw != utc, period


def test_consecutive_windows_tile_without_overlapping():
    """Half-open: the end of one period is the start of the next, so a
    transaction on the boundary is counted once."""

    _, july_end = period_bounds(Period.LAST_MONTH, UTC_ZONE, datetime(2026, 8, 15, tzinfo=UTC))
    august_start, _ = period_bounds(Period.LAST_MONTH, UTC_ZONE, datetime(2026, 9, 15, tzinfo=UTC))

    assert july_end == august_start

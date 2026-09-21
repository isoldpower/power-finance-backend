from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from data_read_core.shared.timestamps import Period, period_bounds

WARSAW = ZoneInfo("Europe/Warsaw")
CHICAGO = ZoneInfo("America/Chicago")
UTC_ZONE = ZoneInfo("UTC")

AUGUST_21_NOON = datetime(2026, 8, 21, 12, tzinfo=UTC)


def test_last_month_is_the_thirty_days_ending_today():
    since, until = period_bounds(Period.LAST_MONTH, UTC_ZONE, AUGUST_21_NOON)

    assert since == datetime(2026, 7, 23, tzinfo=UTC)
    assert until == datetime(2026, 8, 22, tzinfo=UTC)


def test_last_week_is_the_seven_days_ending_today():
    since, until = period_bounds(Period.LAST_WEEK, UTC_ZONE, AUGUST_21_NOON)

    assert since == datetime(2026, 8, 15, tzinfo=UTC)
    assert until == datetime(2026, 8, 22, tzinfo=UTC)


def test_last_year_is_the_three_hundred_and_sixty_five_days_ending_today():
    since, until = period_bounds(Period.LAST_YEAR, UTC_ZONE, AUGUST_21_NOON)

    assert since == datetime(2025, 8, 22, tzinfo=UTC)
    assert until == datetime(2026, 8, 22, tzinfo=UTC)


@pytest.mark.parametrize(
    ("period", "days"),
    [(Period.LAST_WEEK, 7), (Period.LAST_MONTH, 30), (Period.LAST_YEAR, 365)],
)
def test_every_window_spans_exactly_its_advertised_number_of_days(period, days):
    since, until = period_bounds(period, UTC_ZONE, AUGUST_21_NOON)

    assert until - since == timedelta(days=days)


def test_today_is_inside_the_window():
    since, until = period_bounds(Period.LAST_WEEK, UTC_ZONE, AUGUST_21_NOON)

    assert since <= AUGUST_21_NOON < until


def test_the_window_rolls_forward_with_each_new_day():
    today = period_bounds(Period.LAST_MONTH, UTC_ZONE, AUGUST_21_NOON)
    tomorrow = period_bounds(
        Period.LAST_MONTH,
        UTC_ZONE,
        AUGUST_21_NOON + timedelta(days=1),
    )

    assert tomorrow[0] == today[0] + timedelta(days=1)
    assert tomorrow[1] == today[1] + timedelta(days=1)


def test_the_window_is_stable_throughout_a_single_day():
    early = period_bounds(Period.LAST_MONTH, UTC_ZONE, datetime(2026, 8, 21, 0, 0, tzinfo=UTC))
    late = period_bounds(Period.LAST_MONTH, UTC_ZONE, datetime(2026, 8, 21, 23, 59, tzinfo=UTC))

    assert early == late


def test_it_no_longer_snaps_to_the_first_of_the_month():
    since, _ = period_bounds(Period.LAST_MONTH, UTC_ZONE, datetime(2026, 8, 3, 12, tzinfo=UTC))

    assert since == datetime(2026, 7, 5, tzinfo=UTC)


def test_boundaries_are_local_midnight_not_utc_midnight():
    since, until = period_bounds(Period.LAST_MONTH, WARSAW, AUGUST_21_NOON)

    assert since == datetime(2026, 7, 22, 22, tzinfo=UTC)
    assert until == datetime(2026, 8, 21, 22, tzinfo=UTC)


def test_two_zones_on_different_local_dates_get_different_windows():
    instant = datetime(2026, 8, 1, 3, tzinfo=UTC)

    warsaw, _ = period_bounds(Period.LAST_MONTH, WARSAW, instant)
    chicago, _ = period_bounds(Period.LAST_MONTH, CHICAGO, instant)

    assert warsaw != chicago


def test_a_window_crossing_a_daylight_saving_change_still_spans_whole_local_days():
    since, until = period_bounds(Period.LAST_WEEK, WARSAW, datetime(2026, 10, 28, 12, tzinfo=UTC))

    assert since.astimezone(WARSAW).hour == 0
    assert until.astimezone(WARSAW).hour == 0


def test_defaults_to_now_when_no_instant_is_given():
    since, until = period_bounds(Period.LAST_MONTH, UTC_ZONE)

    assert since < until
    assert since.tzinfo is not None


def test_all_time_has_no_bounds():
    assert period_bounds(Period.ALL_TIME, UTC_ZONE) == (None, None)

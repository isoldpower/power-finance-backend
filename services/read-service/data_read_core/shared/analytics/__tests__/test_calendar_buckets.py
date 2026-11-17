from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from data_read_core.shared.analytics import (
    AnalyticsWindow,
    BucketLocator,
    Granularity,
    build_buckets,
    build_days,
    resolve_granularity,
)
from data_read_core.shared.http_contract import ValidationFailed

BERLIN = ZoneInfo("Europe/Berlin")


def _window(since: datetime, until: datetime) -> AnalyticsWindow:
    return AnalyticsWindow(since=since, until=until)


@pytest.mark.parametrize(
    ("length_days", "expected"),
    [
        (45, Granularity.DAY),
        (46, Granularity.WEEK),
        (200, Granularity.WEEK),
        (201, Granularity.MONTH),
    ],
)
def test_granularity_follows_the_window_length(length_days, expected):
    since = datetime(2026, 1, 1, tzinfo=UTC)
    window = _window(since, since + timedelta(days=length_days))

    assert resolve_granularity(None, window) is expected


def test_a_requested_granularity_wins():
    window = _window(datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2, tzinfo=UTC))

    assert resolve_granularity(Granularity.MONTH, window) is Granularity.MONTH


def test_weeks_start_on_monday_and_the_edges_are_clipped():
    window = _window(datetime(2026, 3, 4, 12, tzinfo=UTC), datetime(2026, 3, 18, tzinfo=UTC))

    buckets = build_buckets(window, Granularity.WEEK, ZoneInfo("UTC"))

    assert [bucket.start.isoformat() for bucket in buckets] == [
        "2026-03-04T12:00:00+00:00",
        "2026-03-09T00:00:00+00:00",
        "2026-03-16T00:00:00+00:00",
    ]
    assert buckets[-1].end == window.until


def test_months_roll_over_the_year():
    window = _window(datetime(2026, 11, 15, tzinfo=UTC), datetime(2027, 2, 1, tzinfo=UTC))

    buckets = build_buckets(window, Granularity.MONTH, ZoneInfo("UTC"))

    assert [bucket.end.date().isoformat() for bucket in buckets] == [
        "2026-12-01",
        "2027-01-01",
        "2027-02-01",
    ]


def test_days_follow_local_midnight_across_a_daylight_saving_change():
    window = _window(datetime(2026, 3, 28, 23, tzinfo=UTC), datetime(2026, 3, 30, 22, tzinfo=UTC))

    days = build_days(window, BERLIN)

    assert [day.start.isoformat() for day in days] == [
        "2026-03-28T23:00:00+00:00",
        "2026-03-29T22:00:00+00:00",
    ]
    assert days[0].end - days[0].start == timedelta(hours=23)


def test_too_many_buckets_is_refused():
    window = _window(datetime(2024, 1, 1, tzinfo=UTC), datetime(2026, 1, 1, tzinfo=UTC))

    with pytest.raises(ValidationFailed) as refused:
        build_buckets(window, Granularity.DAY, ZoneInfo("UTC"))

    assert refused.value.details[0].code == "granularity_too_fine"


def test_the_locator_finds_the_bucket_that_holds_an_instant():
    window = _window(datetime(2026, 3, 1, tzinfo=UTC), datetime(2026, 3, 4, tzinfo=UTC))
    locator = BucketLocator(build_days(window, ZoneInfo("UTC")))

    assert locator.index_of(datetime(2026, 3, 2, 23, 59, tzinfo=UTC)) == 1
    assert locator.index_of(datetime(2026, 2, 28, tzinfo=UTC)) is None
    assert locator.index_of(window.until) is None

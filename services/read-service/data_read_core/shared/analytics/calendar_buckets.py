from bisect import bisect_right
from datetime import UTC, date, datetime, time, timedelta
from typing import NamedTuple
from zoneinfo import ZoneInfo

from data_read_core.shared.http_contract import DetailCode, ErrorDetail, ValidationFailed

from .config import (
    DAY_GRANULARITY_LIMIT,
    MAXIMUM_BUCKET_COUNT,
    WEEK_GRANULARITY_LIMIT,
    Granularity,
    Messages,
    ParamsList,
)
from .scope import AnalyticsWindow

ONE_DAY = timedelta(days=1)
ONE_WEEK = timedelta(days=7)
MONTHS_PER_YEAR = 12


class TimeBucket(NamedTuple):
    start: datetime
    end: datetime


class LocalMoment(NamedTuple):
    local_date: date
    iso_weekday: int
    hour: int


def resolve_granularity(
    requested: Granularity | None,
    window: AnalyticsWindow,
) -> Granularity:
    if requested is not None:
        return requested
    if window.length <= DAY_GRANULARITY_LIMIT:
        return Granularity.DAY
    if window.length <= WEEK_GRANULARITY_LIMIT:
        return Granularity.WEEK

    return Granularity.MONTH


def build_buckets(
    window: AnalyticsWindow,
    granularity: Granularity,
    zone: ZoneInfo,
) -> list[TimeBucket]:
    buckets = _walk_buckets(window, granularity, zone, MAXIMUM_BUCKET_COUNT + 1)
    if len(buckets) > MAXIMUM_BUCKET_COUNT:
        raise ValidationFailed(
            details=[
                ErrorDetail(
                    field=ParamsList.GRANULARITY.value,
                    code=DetailCode.GRANULARITY_TOO_FINE,
                    message=Messages.TOO_MANY_BUCKETS.format(maximum=MAXIMUM_BUCKET_COUNT),
                )
            ]
        )

    return buckets


def build_days(window: AnalyticsWindow, zone: ZoneInfo) -> list[TimeBucket]:
    return _walk_buckets(window, Granularity.DAY, zone, maximum_bucket_count=None)


class BucketLocator:
    def __init__(self, buckets: list[TimeBucket]) -> None:
        self._buckets = buckets
        self._bucket_starts = [bucket.start for bucket in buckets]

    def index_of(self, moment: datetime) -> int | None:
        candidate_index = bisect_right(self._bucket_starts, moment) - 1
        if candidate_index < 0:
            return None
        if moment >= self._buckets[candidate_index].end:
            return None

        return candidate_index


def local_moment(moment: datetime, zone: ZoneInfo) -> LocalMoment:
    local_time = moment.astimezone(zone)

    return LocalMoment(
        local_date=local_time.date(),
        iso_weekday=local_time.isoweekday(),
        hour=local_time.hour,
    )


def _walk_buckets(
    window: AnalyticsWindow,
    granularity: Granularity,
    zone: ZoneInfo,
    maximum_bucket_count: int | None,
) -> list[TimeBucket]:
    buckets: list[TimeBucket] = []
    boundary_date = _aligned_date(window.since.astimezone(zone).date(), granularity)
    boundary_start = _local_midnight(boundary_date, zone)

    while boundary_start < window.until:
        if maximum_bucket_count is not None and len(buckets) >= maximum_bucket_count:
            break

        next_boundary_date = _advanced_date(boundary_date, granularity)
        next_boundary_start = _local_midnight(next_boundary_date, zone)
        buckets.append(
            TimeBucket(
                start=max(boundary_start, window.since),
                end=min(next_boundary_start, window.until),
            )
        )
        boundary_date = next_boundary_date
        boundary_start = next_boundary_start

    return buckets


def _aligned_date(local_date: date, granularity: Granularity) -> date:
    if granularity is Granularity.WEEK:
        return local_date - timedelta(days=local_date.isoweekday() - 1)
    if granularity is Granularity.MONTH:
        return local_date.replace(day=1)

    return local_date


def _advanced_date(local_date: date, granularity: Granularity) -> date:
    if granularity is Granularity.WEEK:
        return local_date + ONE_WEEK
    if granularity is Granularity.MONTH:
        month_index = local_date.year * MONTHS_PER_YEAR + local_date.month
        return date(month_index // MONTHS_PER_YEAR, month_index % MONTHS_PER_YEAR + 1, 1)

    return local_date + ONE_DAY


def _local_midnight(local_date: date, zone: ZoneInfo) -> datetime:
    return datetime.combine(local_date, time.min, tzinfo=zone).astimezone(UTC)

from data_read_core.shared.analytics import (
    AnalyticsScope,
    Granularity,
    TimeBucket,
    present_analytics_category,
    present_scope_meta,
)
from data_read_core.shared.money import money_at_scale
from data_read_core.shared.timestamps import to_iso

from ..config import SeriesKind
from ..dtos import CategorySeriesDTO, CategoryTrendsDTO


async def present_category_trends(
    category_trends: CategoryTrendsDTO,
    buckets: list[TimeBucket],
    currency: str,
) -> dict:
    return {
        "type": category_trends.side.value,
        "buckets": [
            {"start": to_iso(bucket.start), "end": to_iso(bucket.end)} for bucket in buckets
        ],
        "series": [await _present_series(series, currency) for series in category_trends.series],
    }


def present_meta(scope: AnalyticsScope, granularity: Granularity, cached: bool) -> dict:
    return present_scope_meta(scope, cached, granularity=granularity.value)


async def _present_series(series: CategorySeriesDTO, currency: str) -> dict:
    return {
        "key": series.key,
        "category": present_analytics_category(series.category),
        "kind": (SeriesKind.OTHER if series.is_other else SeriesKind.CATEGORY).value,
        "total": await money_at_scale(series.total, currency),
        "points": [await money_at_scale(point, currency) for point in series.points],
    }

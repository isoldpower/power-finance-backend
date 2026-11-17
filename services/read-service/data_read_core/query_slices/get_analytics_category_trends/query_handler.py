from decimal import Decimal
from typing import NamedTuple

from data_read_core.shared.analytics import (
    ZERO,
    AnalyticsCategory,
    AnalyticsLedger,
    AnalyticsReportHandler,
    BucketLocator,
    LedgerRow,
    ReservedTokens,
    category_token,
    tally_by_category,
)

from .config import REPORT_NAME
from .dtos import CategorySeriesDTO, CategoryTrendsDTO, GetAnalyticsCategoryTrendsQuery


class FeaturedCategories(NamedTuple):
    categories: list[AnalyticsCategory | None]
    has_other: bool


class GetAnalyticsCategoryTrendsQueryHandler(
    AnalyticsReportHandler[GetAnalyticsCategoryTrendsQuery]
):
    report_name = REPORT_NAME
    report_type = CategoryTrendsDTO

    async def _build(self, query: GetAnalyticsCategoryTrendsQuery) -> CategoryTrendsDTO:
        ledger = await AnalyticsLedger.load(query.scope, self._rate_service)
        rows = await ledger.fetch_flows(query.scope.window, side=query.side)
        featured = _featured_categories(ledger, rows, query)
        points_by_category = {
            category: [ZERO] * len(query.buckets) for category in featured.categories
        }
        other_points = [ZERO] * len(query.buckets)
        bucket_locator = BucketLocator(query.buckets)

        for row in rows:
            bucket_index = bucket_locator.index_of(row.created_at)
            if bucket_index is None:
                continue

            target_points = points_by_category.get(row.category, other_points)
            target_points[bucket_index] += ledger.converted_magnitude(row)

        series = [
            CategorySeriesDTO(
                key=category_token(category),
                category=category,
                is_other=False,
                points=points_by_category[category],
            )
            for category in _ordered_by_total(featured.categories, points_by_category)
        ]
        if featured.has_other:
            series.append(
                CategorySeriesDTO(
                    key=ReservedTokens.OTHER.value,
                    category=None,
                    is_other=True,
                    points=other_points,
                )
            )

        return CategoryTrendsDTO(side=query.side, series=series)


def _featured_categories(
    ledger: AnalyticsLedger,
    rows: list[LedgerRow],
    query: GetAnalyticsCategoryTrendsQuery,
) -> FeaturedCategories:
    if query.scope.categories is not None:
        return FeaturedCategories(categories=list(query.scope.categories), has_other=False)

    ranked_categories = [tally.category for tally in tally_by_category(ledger, rows)]

    return FeaturedCategories(
        categories=ranked_categories[: query.limit],
        has_other=len(ranked_categories) > query.limit,
    )


def _ordered_by_total(
    categories: list[AnalyticsCategory | None],
    points_by_category: dict[AnalyticsCategory | None, list[Decimal]],
) -> list[AnalyticsCategory | None]:
    return sorted(
        categories,
        key=lambda category: sum(points_by_category[category], ZERO),
        reverse=True,
    )

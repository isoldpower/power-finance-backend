from dataclasses import dataclass
from decimal import Decimal

from data_read_core.shared.analytics import (
    ZERO,
    AnalyticsCategory,
    Granularity,
    LedgerSide,
    ScopedAnalyticsQuery,
    TimeBucket,
)


@dataclass(frozen=True)
class GetAnalyticsCategoryTrendsQuery(ScopedAnalyticsQuery):
    side: LedgerSide
    granularity: Granularity
    buckets: list[TimeBucket]
    limit: int

    @property
    def report_parameters(self) -> dict:
        return {
            "type": self.side.value,
            "granularity": self.granularity.value,
            "limit": self.limit,
        }


@dataclass(frozen=True)
class CategorySeriesDTO:
    key: str
    category: AnalyticsCategory | None
    is_other: bool
    points: list[Decimal]

    @property
    def total(self) -> Decimal:
        return sum(self.points, ZERO)


@dataclass(frozen=True)
class CategoryTrendsDTO:
    side: LedgerSide
    series: list[CategorySeriesDTO]

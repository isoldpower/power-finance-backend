from dataclasses import dataclass
from decimal import Decimal

from data_read_core.shared.analytics import AnalyticsScope, Granularity, LedgerSide, TimeBucket


@dataclass(frozen=True)
class GetAnalyticsCategoryTrendsQuery:
    scope: AnalyticsScope
    side: LedgerSide
    granularity: Granularity
    buckets: list[TimeBucket]
    limit: int

    @property
    def user_id(self) -> int:
        return self.scope.user_id

    @property
    def cache_signature(self) -> dict:
        return {
            **self.scope.cache_signature,
            "type": self.side.value,
            "granularity": self.granularity.value,
            "limit": self.limit,
        }


@dataclass(frozen=True)
class CategorySeriesDTO:
    key: str
    category: str | None
    is_other: bool
    points: list[Decimal]

    @property
    def total(self) -> Decimal:
        return sum(self.points, Decimal(0))


@dataclass(frozen=True)
class CategoryTrendsDTO:
    side: LedgerSide
    series: list[CategorySeriesDTO]

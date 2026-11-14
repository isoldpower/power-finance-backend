from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from data_read_core.shared.analytics import AnalyticsScope, Granularity, TimeBucket


@dataclass(frozen=True)
class GetAnalyticsCashFlowQuery:
    scope: AnalyticsScope
    granularity: Granularity
    buckets: list[TimeBucket]

    @property
    def user_id(self) -> int:
        return self.scope.user_id

    @property
    def cache_signature(self) -> dict:
        return {**self.scope.cache_signature, "granularity": self.granularity.value}


@dataclass(frozen=True)
class CashFlowBucketDTO:
    start: datetime
    end: datetime
    inflow: Decimal
    outflow: Decimal
    transactions_count: int
    closing_balance: Decimal

    @property
    def net(self) -> Decimal:
        return self.inflow - self.outflow


@dataclass(frozen=True)
class CashFlowDTO:
    buckets: list[CashFlowBucketDTO]

    @property
    def inflow(self) -> Decimal:
        return sum((bucket.inflow for bucket in self.buckets), Decimal(0))

    @property
    def outflow(self) -> Decimal:
        return sum((bucket.outflow for bucket in self.buckets), Decimal(0))

    @property
    def net(self) -> Decimal:
        return self.inflow - self.outflow

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from data_read_core.shared.analytics import (
    ZERO,
    Granularity,
    ScopedAnalyticsQuery,
    TimeBucket,
)


@dataclass(frozen=True)
class GetAnalyticsCashFlowQuery(ScopedAnalyticsQuery):
    granularity: Granularity
    buckets: list[TimeBucket]

    @property
    def report_parameters(self) -> dict:
        return {"granularity": self.granularity.value}


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
        return sum((bucket.inflow for bucket in self.buckets), ZERO)

    @property
    def outflow(self) -> Decimal:
        return sum((bucket.outflow for bucket in self.buckets), ZERO)

    @property
    def net(self) -> Decimal:
        return self.inflow - self.outflow

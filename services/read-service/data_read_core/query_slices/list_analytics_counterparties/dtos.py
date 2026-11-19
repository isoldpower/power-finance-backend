from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from data_read_core.shared.analytics import (
    AnalyticsCategory,
    LedgerSide,
    ScopedAnalyticsQuery,
)


@dataclass(frozen=True)
class ListAnalyticsCounterpartiesQuery(ScopedAnalyticsQuery):
    side: LedgerSide
    limit: int

    @property
    def report_parameters(self) -> dict:
        return {"type": self.side.value, "limit": self.limit}


@dataclass(frozen=True)
class CounterpartyDTO:
    name: str
    category: AnalyticsCategory | None
    amount: Decimal
    share: Decimal
    transactions_count: int
    last_seen_at: datetime

    @property
    def average(self) -> Decimal:
        return self.amount / self.transactions_count


@dataclass(frozen=True)
class CounterpartiesDTO:
    counterparties: list[CounterpartyDTO]
    total_counterparties: int

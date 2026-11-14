from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from data_read_core.shared.analytics import AnalyticsScope, LedgerSide


@dataclass(frozen=True)
class ListAnalyticsCounterpartiesQuery:
    scope: AnalyticsScope
    side: LedgerSide
    limit: int

    @property
    def user_id(self) -> int:
        return self.scope.user_id

    @property
    def cache_signature(self) -> dict:
        return {**self.scope.cache_signature, "type": self.side.value, "limit": self.limit}


@dataclass(frozen=True)
class CounterpartyDTO:
    name: str
    category: str | None
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

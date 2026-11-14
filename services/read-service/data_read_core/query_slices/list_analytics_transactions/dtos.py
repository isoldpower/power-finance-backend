from dataclasses import dataclass
from decimal import Decimal

from data_read_core.shared.analytics import AnalyticsScope, LedgerSide, TransactionBriefDTO

from .config import TransactionOrder


@dataclass(frozen=True)
class ListAnalyticsTransactionsQuery:
    scope: AnalyticsScope
    side: LedgerSide | None
    counterparty_name: str | None
    order: TransactionOrder
    limit: int

    @property
    def user_id(self) -> int:
        return self.scope.user_id

    @property
    def cache_signature(self) -> dict:
        return {
            **self.scope.cache_signature,
            "type": self.side.value if self.side else None,
            "name": self.counterparty_name,
            "order": self.order.value,
            "limit": self.limit,
        }


@dataclass(frozen=True)
class AnalyticsTransactionsDTO:
    transactions: list[TransactionBriefDTO]
    total: int
    total_inflow: Decimal
    total_outflow: Decimal

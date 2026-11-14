from dataclasses import dataclass
from decimal import Decimal

from data_read_core.shared.analytics import AnalyticsScope, LedgerWallet

from .config import FlowNodeKind


@dataclass(frozen=True)
class GetAnalyticsMoneyFlowQuery:
    scope: AnalyticsScope

    @property
    def user_id(self) -> int:
        return self.scope.user_id

    @property
    def cache_signature(self) -> dict:
        return self.scope.cache_signature


@dataclass(frozen=True)
class FlowNodeDTO:
    identifier: str
    kind: FlowNodeKind
    label: str
    category: str | None
    wallet: LedgerWallet | None
    amount: Decimal


@dataclass(frozen=True)
class FlowLinkDTO:
    source: str
    target: str
    amount: Decimal


@dataclass(frozen=True)
class MoneyFlowDTO:
    nodes: list[FlowNodeDTO]
    links: list[FlowLinkDTO]
    inflow: Decimal
    outflow: Decimal

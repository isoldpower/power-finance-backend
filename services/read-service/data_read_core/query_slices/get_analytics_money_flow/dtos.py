from dataclasses import dataclass
from decimal import Decimal

from data_read_core.shared.analytics import (
    AnalyticsCategory,
    LedgerWallet,
    ScopedAnalyticsQuery,
)

from .config import FlowNodeKind


@dataclass(frozen=True)
class GetAnalyticsMoneyFlowQuery(ScopedAnalyticsQuery):
    pass


@dataclass(frozen=True)
class FlowNodeDTO:
    identifier: str
    kind: FlowNodeKind
    label: str
    category: AnalyticsCategory | None
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

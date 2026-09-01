from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from data_read_core.shared.metrics import MetricsWindow
from data_read_core.shared.postgres_orm import AccountGroups


class Section(StrEnum):
    BALANCE = "balance"
    NET_WORTH = "net-worth"
    CASH_FLOW = "cash-flow"

    @property
    def key(self) -> str:
        return self.value.replace("-", "_")


ALL_SECTIONS = tuple(Section)


class Direction(StrEnum):
    UP = "up"
    DOWN = "down"
    FLAT = "flat"


@dataclass(frozen=True)
class GetMetricsQuery:
    user_id: int
    currency: str
    window: MetricsWindow
    points: int
    sections: frozenset[Section]

    def wants(self, section: Section) -> bool:
        return section in self.sections

    @property
    def section_signature(self) -> str:
        return ",".join(sorted(section.value for section in self.sections))


@dataclass(frozen=True)
class BalanceSheetDTO:
    assets: Decimal
    liabilities: Decimal
    equity: Decimal
    unbalanced_dispatches: int

    @property
    def drift(self) -> Decimal:
        return self.assets - self.liabilities - self.equity

    @property
    def identity_holds(self) -> bool:
        return self.drift == 0

    @property
    def balanced(self) -> bool:
        return self.identity_holds and self.unbalanced_dispatches == 0


@dataclass(frozen=True)
class SeriesPointDTO:
    timestamp: datetime
    amount: Decimal


@dataclass(frozen=True)
class NetWorthDTO:
    total_amount: Decimal
    opening_balance: Decimal
    points_series: list[SeriesPointDTO]

    @property
    def net_change(self) -> Decimal:
        return self.total_amount - self.opening_balance

    @property
    def direction(self) -> Direction:
        if self.net_change > 0:
            return Direction.UP
        if self.net_change < 0:
            return Direction.DOWN

        return Direction.FLAT

    @property
    def percentage(self) -> Decimal | None:
        if self.opening_balance == 0:
            return None

        return (self.net_change / abs(self.opening_balance)) * 100


@dataclass(frozen=True)
class CashFlowDTO:
    inflow: Decimal
    outflow: Decimal

    @property
    def total_net(self) -> Decimal:
        return self.inflow - self.outflow

    @property
    def savings_rate(self) -> Decimal | None:
        if self.inflow == 0:
            return None

        return (self.total_net / self.inflow) * 100


@dataclass(frozen=True)
class MetricsDTO:
    currency: str
    balance: BalanceSheetDTO | None
    net_worth: NetWorthDTO | None
    cash_flow: CashFlowDTO | None


EMPTY_GROUPS: dict[str, Decimal] = {group.value: Decimal(0) for group in AccountGroups}

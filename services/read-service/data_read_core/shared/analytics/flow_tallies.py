from decimal import Decimal
from typing import NamedTuple

from .config import ZERO, LedgerSide


class FlowTally(NamedTuple):
    inflow: Decimal = ZERO
    outflow: Decimal = ZERO
    transactions_count: int = 0

    @property
    def net(self) -> Decimal:
        return self.inflow - self.outflow

    def including(self, side: LedgerSide, converted_amount: Decimal) -> "FlowTally":
        return FlowTally(
            inflow=self.inflow + (converted_amount if side is LedgerSide.INCOME else ZERO),
            outflow=self.outflow + (converted_amount if side is LedgerSide.EXPENSE else ZERO),
            transactions_count=self.transactions_count + 1,
        )

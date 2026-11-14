from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .config import LedgerSide


@dataclass(frozen=True, slots=True)
class LedgerWallet:
    identifier: str
    name: str
    color: str
    currency: str
    favorite: bool


@dataclass(frozen=True, slots=True)
class LedgerRow:
    identifier: str
    wallet_identifier: str
    signed_amount: Decimal
    currency: str
    name: str
    category: str | None
    chain_identifier: str | None
    created_at: datetime

    @property
    def is_transfer(self) -> bool:
        return self.chain_identifier is not None

    @property
    def side(self) -> LedgerSide:
        return LedgerSide.EXPENSE if self.signed_amount < 0 else LedgerSide.INCOME

    @property
    def magnitude(self) -> Decimal:
        return abs(self.signed_amount)

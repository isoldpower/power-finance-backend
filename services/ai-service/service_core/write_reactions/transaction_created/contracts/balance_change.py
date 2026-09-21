from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class BalanceChange:
    account_id: UUID
    group: str
    name: str
    currency_code: str
    previous: Decimal
    current: Decimal

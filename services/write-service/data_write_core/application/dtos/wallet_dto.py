from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class WalletDTO:
    id: UUID
    user_id: int
    name: str
    balance_amount: Decimal
    currency: str
    created_at: datetime
    updated_at: datetime
    category: str = ""
    color: str = ""
    favorite: bool = False
    zero_balance: Decimal = Decimal("0")
    deleted_at: datetime | None = None

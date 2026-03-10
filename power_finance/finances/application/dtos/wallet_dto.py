from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID
from datetime import datetime


@dataclass
class WalletDTO:
    id: UUID
    user_id: int
    name: str
    balance_amount: Decimal
    currency: str
    credit: bool
    created_at: datetime
    updated_at: datetime

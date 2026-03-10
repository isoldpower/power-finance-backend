from dataclasses import dataclass
from typing import Optional
from uuid import UUID
from datetime import datetime

from ..value_objects import Money


@dataclass
class Wallet:
    """
    Represents a user's financial account that stores balance in a specific currency and can be
    whether credit or debit. Each user can have multiple wallets
    """

    id: UUID
    user_id: int
    name: str
    balance: Money
    credit: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]
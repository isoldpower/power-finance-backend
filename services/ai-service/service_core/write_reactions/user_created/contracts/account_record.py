from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AccountRecord:
    """An account as it exists once written down."""

    account_id: UUID
    group: str
    name: str
    balance: Decimal
    created_at: datetime

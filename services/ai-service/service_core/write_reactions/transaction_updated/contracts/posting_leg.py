from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PostingLeg:
    """One side of a double entry, against an account that already exists."""

    account_id: UUID
    title: str
    debit: bool
    amount: Decimal
    position: int
    icon: str = ""
    currency_code: str | None = None

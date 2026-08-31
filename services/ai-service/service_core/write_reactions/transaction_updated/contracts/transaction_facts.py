from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TransactionFacts:
    """Everything the dispatcher knows about a transaction."""

    id: UUID
    user_id: int
    container_id: UUID
    container_kind: str
    amount: Decimal
    created_at: datetime

    currency_code: str = ""
    name: str = ""
    category: str = ""
    evidence_url: str = ""
    origin: str = ""
    chain_id: str = ""

    updated_at: datetime | None = None
    deleted_at: datetime | None = None

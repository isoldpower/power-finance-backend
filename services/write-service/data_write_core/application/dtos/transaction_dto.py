from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from data_write_core.domain.value_objects import TransactionOrigin, TransactionType

from .goal_dto import MoneyContainerDTO


@dataclass(frozen=True)
class TransactionDTO:
    id: UUID
    user_id: int
    name: str
    amount: Decimal
    currency_code: str
    transaction_type: TransactionType
    origin: TransactionOrigin
    container: MoneyContainerDTO
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    category: str | None = None
    evidence_url: str | None = None
    chain_id: UUID | None = None


@dataclass(frozen=True)
class TransactionChainDTO:
    chain_id: UUID
    transactions: list[TransactionDTO]


@dataclass(frozen=True)
class TransactionPlainDTO:
    id: UUID
    amount: Decimal
    currency_code: str
    container_id: str
    created_at: datetime
    transaction_id: UUID | None = None
    cancels_other: UUID | None = None
    adjusts_other: UUID | None = None

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from .wallet_dto import WalletDTO

from finances.domain.entities import TransactionType, ExpenseCategory


@dataclass(frozen=True)
class TransactionParticipantDTO:
    wallet: WalletDTO
    amount: Decimal


@dataclass(frozen=True)
class TransactionParticipantPlainDTO:
    wallet_id: UUID
    amount: Decimal


@dataclass(frozen=True)
class TransactionPlainDTO:
    id: UUID
    sender: TransactionParticipantPlainDTO | None
    receiver: TransactionParticipantPlainDTO | None
    description: str
    created_at: datetime
    type: TransactionType
    category: ExpenseCategory


@dataclass(frozen=True)
class TransactionDTO:
    id: UUID
    sender: TransactionParticipantDTO | None
    receiver: TransactionParticipantDTO | None
    description: str
    created_at: datetime
    type: TransactionType
    category: ExpenseCategory
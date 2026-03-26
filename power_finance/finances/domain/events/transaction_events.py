from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from .domain_event import DomainEvent


@dataclass(frozen=True)
class TransactionEventParticipant:
    wallet_id: UUID
    currency_code: str
    amount: Decimal


@dataclass(frozen=True)
class TransactionCreatedEvent(DomainEvent):
    transaction_id: UUID
    created_at: datetime
    sender: TransactionEventParticipant | None
    receiver: TransactionEventParticipant | None
    description: str | None


@dataclass(frozen=True)
class UpdateTransactionData:
    sender: TransactionEventParticipant | None
    receiver: TransactionEventParticipant | None
    category: str | None
    description: str | None


@dataclass(frozen=True)
class TransactionUpdatedEvent(DomainEvent):
    old_transaction: UpdateTransactionData
    current_transaction: UpdateTransactionData
    transaction_id: UUID
    updated_at: datetime


@dataclass(frozen=True)
class TransactionDeletedEvent(DomainEvent):
    transaction_id: UUID
    created_at: datetime
    sender: TransactionEventParticipant | None
    receiver: TransactionEventParticipant | None
    description: str | None

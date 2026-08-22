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
    wallet_id: UUID
    user_id: int
    amount: Decimal
    transaction_id: UUID
    created_at: datetime


@dataclass(frozen=True)
class TransactionUpdatedEvent(DomainEvent):
    transaction_id: UUID
    wallet_id: UUID
    user_id: int
    previous_amount: Decimal
    new_amount: Decimal
    updated_at: datetime


@dataclass(frozen=True)
class TransactionMetadataUpdatedEvent(DomainEvent):
    transaction_id: UUID
    user_id: int
    name: str
    category: str | None
    evidence_url: str | None
    updated_at: datetime


@dataclass(frozen=True)
class TransactionDeletedEvent(DomainEvent):
    transaction_id: UUID
    wallet_id: UUID
    user_id: int
    amount: Decimal
    cancelled_by: UUID
    created_at: datetime

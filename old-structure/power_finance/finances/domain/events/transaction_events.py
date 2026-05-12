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
class TransactionDeletedEvent(DomainEvent):
    transaction_id: UUID
    wallet_id: UUID
    user_id: int
    amount: Decimal
    cancelled_by: UUID
    created_at: datetime

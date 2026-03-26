from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from .domain_event import DomainEvent


@dataclass(frozen=True)
class TransactionUpdatedEvent(DomainEvent):
    transaction_id: UUID
    updated_at: datetime
    sender: TransactionEventParticipant | None
    receiver: TransactionEventParticipant | None
    description: str | None
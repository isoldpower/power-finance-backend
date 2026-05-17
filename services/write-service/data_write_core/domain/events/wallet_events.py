from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from .domain_event import DomainEvent


@dataclass(frozen=True)
class WalletDeletedEvent(DomainEvent):
    wallet_id: UUID
    user_id: int
    deleted_at: datetime


@dataclass(frozen=True)
class WalletUpdatedEvent(DomainEvent):
    wallet_id: UUID
    user_id: int
    previous_title: str
    new_title: str
    updated_at: datetime

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from .domain_event import DomainEvent


@dataclass(frozen=True)
class GoalDeletedEvent(DomainEvent):
    goal_id: UUID
    user_id: int
    deleted_at: datetime


@dataclass(frozen=True)
class GoalUpdatedEvent(DomainEvent):
    goal_id: UUID
    user_id: int
    previous_title: str
    new_title: str
    updated_at: datetime
    target: Decimal
    finish_at: datetime | None = None
    url: str | None = None

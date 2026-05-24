from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID


class OutboxEventBase(ABC):
    """Contract for any outbox event a repository may append.

    Concrete events declare `AGGREGATE_TYPE` / `EVENT_TYPE` ClassVars,
    plus the per-instance `event_id` / `occurred_at` fields used by the
    outbox row layout. Declaring them here keeps repository implementations
    Liskov-substitutable behind the `OutboxRepository.append` signature."""

    AGGREGATE_TYPE: ClassVar[str]
    EVENT_TYPE: ClassVar[str]
    SCHEMA_VERSION: ClassVar[int] = 1

    event_id: UUID
    occurred_at: datetime

    @property
    @abstractmethod
    def aggregate_id(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def to_payload(self) -> dict[str, Any]:
        raise NotImplementedError()

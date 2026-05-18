from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from data_write_core.infrastructure.outbox_saga.outbox_events import OutboxEvent


class OutboxRepository(ABC):
    """Persists outbox events to durable storage so a downstream
    publisher (Debezium) can stream them to Kafka. Callers must
    invoke `append` inside the same DB transaction as the business
    write that produced the event — that's what makes the outbox
    pattern atomic."""

    @abstractmethod
    async def append(self, event: "OutboxEvent") -> None:
        raise NotImplementedError()

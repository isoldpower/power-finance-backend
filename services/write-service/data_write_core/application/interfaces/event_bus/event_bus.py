from abc import ABC, abstractmethod
from typing import Protocol, TypeVar

from data_write_core.domain.events import DomainEvent

EventType = TypeVar("EventType", bound=DomainEvent)
_EventTypeContra = TypeVar("_EventTypeContra", bound=DomainEvent, contravariant=True)


class AsyncEventHandler(Protocol[_EventTypeContra]):
    async def __call__(self, event: _EventTypeContra) -> None: ...


EventHandler = AsyncEventHandler


class EventBus(ABC):
    """In-process pub/sub for domain events.

    Subscribers see only events whose underlying state changes have
    already committed (handlers call `publish` after the SAGA + outbox
    writes succeed). Used for cross-aggregate reactions: cache
    invalidations, fraud-counter bumps, derived projections — NOT
    for inter-service messaging. Inter-service communication goes
    through the outbox / Kafka (`application/outbox/events`); the
    two pipelines are deliberately disjoint."""

    @abstractmethod
    async def publish(self, events: list[DomainEvent]) -> None:
        raise NotImplementedError()

    @abstractmethod
    def subscribe(
        self,
        event_type: type[EventType],
        handler: AsyncEventHandler[EventType],
    ) -> None:
        raise NotImplementedError()

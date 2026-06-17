from abc import ABC, abstractmethod
from typing import Protocol, TypeVar

from data_write_core.domain.events import DomainEvent

EventType = TypeVar("EventType", bound=DomainEvent)
_EventTypeContra = TypeVar("_EventTypeContra", bound=DomainEvent, contravariant=True)


class AsyncEventHandler(Protocol[_EventTypeContra]):
    async def __call__(self, event: _EventTypeContra) -> None: ...


EventHandler = AsyncEventHandler


class EventBus(ABC):
    """In-process pub/sub for committed domain events: cross-aggregate
    reactions only, never inter-service messaging (that goes via the outbox)."""

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

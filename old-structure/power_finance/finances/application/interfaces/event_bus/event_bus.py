from abc import ABC, abstractmethod
from typing import TypeVar, Protocol

from finances.domain.events import DomainEvent


EventType = TypeVar("EventType", bound=DomainEvent)

class AsyncEventHandler(Protocol[EventType]):
    async def __call__(self, event: EventType) -> None:
        pass


EventHandler = AsyncEventHandler[EventType]


class EventBus(ABC):
    @abstractmethod
    async def publish(self, events: list[DomainEvent]) -> None:
        raise NotImplementedError()

    @abstractmethod
    def subscribe(self, event_type: type[EventType], handler: EventHandler) -> None:
        raise NotImplementedError()

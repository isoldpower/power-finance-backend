from abc import ABC, abstractmethod
from typing import TypeVar, Protocol, Union

from finances.domain.events import DomainEvent


EventType = TypeVar("EventType", bound=DomainEvent)

class SyncEventHandler(Protocol[EventType]):
    def __call__(self, event: EventType) -> None:
        pass

class AsyncEventHandler(Protocol[EventType]):
    async def __call__(self, event: EventType) -> None:
        pass


EventHandler = Union[SyncEventHandler[EventType], AsyncEventHandler[EventType]]


class EventBus(ABC):
    @abstractmethod
    def publish(self, events: list[DomainEvent]) -> None:
        raise NotImplementedError()

    @abstractmethod
    def subscribe(self, event_type: type[EventType], handler: EventHandler) -> None:
        raise NotImplementedError()

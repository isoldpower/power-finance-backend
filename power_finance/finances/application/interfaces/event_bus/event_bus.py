from abc import ABC, abstractmethod
from typing import TypeVar, Protocol

from finances.domain.events import DomainEvent


EventType = TypeVar("EventType", bound=DomainEvent)

class EventHandler(Protocol[EventType]):
    def __call__(self, event: EventType) -> None:
        pass


class EventBus(ABC):
    @abstractmethod
    def publish(self, events: list[DomainEvent]) -> None:
        raise NotImplementedError()

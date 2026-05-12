from abc import ABC, abstractmethod

from finances.domain.events import EventCollector


class UseCaseBase(ABC):
    @abstractmethod
    async def handle(self):
        raise NotImplementedError()


class UseCaseEvently(UseCaseBase):
    event_collector: EventCollector

    def __init__(self):
        self.event_collector = EventCollector()

    @abstractmethod
    async def handle(self, *args, **kwargs) -> None:
        raise NotImplementedError()
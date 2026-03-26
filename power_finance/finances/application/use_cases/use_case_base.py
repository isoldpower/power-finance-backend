from abc import ABC, abstractmethod

from finances.domain.events import EventCollector


class UseCaseBase(ABC):
    @abstractmethod
    def handle(self):
        raise NotImplementedError()


class UseCaseEvently(UseCaseBase):
    event_collector: EventCollector

    def __init__(self):
        self.event_collector = EventCollector()

    @abstractmethod
    def handle(self):
        raise NotImplementedError()
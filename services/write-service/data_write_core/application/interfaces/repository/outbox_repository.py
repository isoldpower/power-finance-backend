from abc import ABC, abstractmethod

from ..outbox_event import OutboxEventBase


class OutboxRepository(ABC):
    @abstractmethod
    async def append(self, event: "OutboxEventBase") -> int:
        raise NotImplementedError()

    @abstractmethod
    async def get_latest_sequence(self) -> int:
        raise NotImplementedError()

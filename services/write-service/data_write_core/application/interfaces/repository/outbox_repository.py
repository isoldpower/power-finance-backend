from abc import ABC, abstractmethod

from data_write_core.domain.value_objects import OutboxEntry


class OutboxRepository(ABC):
    @abstractmethod
    async def append(self, entry: OutboxEntry) -> int:
        raise NotImplementedError()

    @abstractmethod
    async def get_latest_sequence(self) -> int:
        raise NotImplementedError()

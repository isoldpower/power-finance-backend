from abc import ABC, abstractmethod
from collections.abc import Sequence

from .contracts import OutboxEntry


class OutboxRepository(ABC):
    @abstractmethod
    async def publish(self, entries: Sequence[OutboxEntry]) -> None:
        """Write these rows in the caller's transaction, in the order given."""

        raise NotImplementedError()

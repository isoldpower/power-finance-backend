from abc import ABC, abstractmethod
from uuid import UUID

from ..contracts import RemovedPosting


class EntryRepository(ABC):
    @abstractmethod
    async def remove_for_transaction(self, transaction_id: UUID) -> list[RemovedPosting]:
        raise NotImplementedError()

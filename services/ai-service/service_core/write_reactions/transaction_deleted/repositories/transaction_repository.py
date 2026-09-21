from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID


class ProjectedTransactionRepository(ABC):
    @abstractmethod
    async def soft_delete(
        self,
        transaction_id: UUID,
        deleted_at: datetime,
        applied_seq: int,
    ) -> None:
        raise NotImplementedError()

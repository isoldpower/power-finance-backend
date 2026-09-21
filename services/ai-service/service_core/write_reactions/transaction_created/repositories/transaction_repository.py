from abc import ABC, abstractmethod
from uuid import UUID

from ..contracts import TransactionFacts


class ProjectedTransactionRepository(ABC):
    @abstractmethod
    async def get(self, transaction_id: UUID) -> TransactionFacts | None:
        raise NotImplementedError()

    @abstractmethod
    async def project(self, facts: TransactionFacts, applied_seq: int) -> None:
        raise NotImplementedError()

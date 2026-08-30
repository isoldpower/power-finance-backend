from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from ..contracts import TransactionFacts


class ProjectedTransactionRepository(ABC):
    @abstractmethod
    async def get(self, transaction_id: UUID) -> TransactionFacts | None:
        raise NotImplementedError()

    @abstractmethod
    async def update_amount(
        self,
        transaction_id: UUID,
        amount: Decimal,
        updated_at: datetime,
        applied_seq: int,
    ) -> None:
        raise NotImplementedError()

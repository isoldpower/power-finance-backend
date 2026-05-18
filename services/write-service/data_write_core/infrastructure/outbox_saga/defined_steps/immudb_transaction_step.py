from data_write_core.application.interfaces import TransactionRepository
from data_write_core.domain.entities import TransactionEntity
from data_write_core.domain.events import EventCollector

from ..saga_step import SagaStep


class ImmudbTransactionStep(SagaStep):
    """ImmuDB side of the transactions SAGA."""

    def __init__(
        self,
        repository: TransactionRepository,
        transaction: TransactionEntity,
    ) -> None:
        self._repository = repository
        self._transaction = transaction

    async def forward(self) -> None:
        await self._repository.create_transaction(self._transaction)

    async def compensate(self) -> None:
        inverse_transaction = self._transaction.create_inverse(
            event_collector=EventCollector(),
        )

        await self._repository.create_transaction(inverse_transaction)

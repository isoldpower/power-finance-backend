from saga_pattern_py import SagaStep

from data_write_core.application.interfaces import MoneyFlowRepository
from data_write_core.domain.entities import MoneyFlowEntity
from data_write_core.domain.events import EventCollector


class ImmudbMoneyFlowStep(SagaStep[None]):
    """ImmuDB side of the transactions SAGA."""

    def __init__(
        self,
        repository: MoneyFlowRepository,
        transaction: MoneyFlowEntity,
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

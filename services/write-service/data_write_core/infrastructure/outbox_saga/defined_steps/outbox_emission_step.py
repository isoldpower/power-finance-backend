from collections.abc import Sequence

from data_write_core.application.db_utils import aatomic
from data_write_core.application.interfaces import OutboxRepository
from data_write_core.infrastructure.outbox_saga.outbox_events import OutboxEvent

from ..saga_step import SagaStep


class OutboxEmissionStep(SagaStep):
    """Broadcast side of a SAGA — the announce-it / final step."""

    def __init__(
        self,
        outbox_repository: OutboxRepository,
        events: Sequence[OutboxEvent],
    ) -> None:
        self._outbox_repository = outbox_repository
        self._events: list[OutboxEvent] = list(events)

    async def forward(self) -> None:
        async with aatomic():
            for event in self._events:
                await self._outbox_repository.append(event)

    async def compensate(self) -> None:
        raise NotImplementedError(
            "OutboxEmissionStep compensation should never be called as it is consider the "
            "final step of the pipeline."
        )

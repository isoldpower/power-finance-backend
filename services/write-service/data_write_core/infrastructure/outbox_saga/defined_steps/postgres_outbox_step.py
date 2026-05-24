from collections.abc import Sequence

from data_write_core.application.db_utils import aatomic
from data_write_core.application.interfaces import OutboxRepository
from data_write_core.infrastructure.outbox_saga.outbox_events import OutboxEvent

from ..saga_step import OutboxSagaStep


class PostgresOutboxEmissionStep(OutboxSagaStep):
    """Broadcast side of a SAGA — the announce-it / final step.

    After a successful `forward()`, `last_appended_seq` returns the
    BIGSERIAL id of the most recently appended outbox row. Command
    handlers read this and forward it up to the view as
    `X-Write-Version`. Because BIGSERIAL is monotonic within a Postgres
    instance, the last id is also the highest, so multi-event sagas
    pick up the correct minimum-version token for the client."""

    def __init__(
        self,
        outbox_repository: OutboxRepository,
        events: Sequence[OutboxEvent],
    ) -> None:
        super().__init__()

        self._outbox_repository = outbox_repository
        self._events: list[OutboxEvent] = list(events)

    async def forward(self) -> int:
        async with aatomic():
            for event in self._events:
                sequence = await self._outbox_repository.append(event)
                self._appended_sequences.append(sequence)

        return self.last_appended_sequence

    async def compensate(self) -> None:
        raise NotImplementedError(
            "OutboxEmissionStep compensation should never be called as it is consider the "
            "final step of the pipeline."
        )

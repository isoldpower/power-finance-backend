from collections.abc import Sequence

from data_write_core.application.db_utils import aatomic
from data_write_core.application.interfaces import OutboxRepository
from data_write_core.domain.value_objects import OutboxEntry

from ..saga_step import OutboxSagaStep


class PostgresOutboxEmissionStep(OutboxSagaStep):
    """Final saga step. Appends outbox entries; last_appended_sequence is returned as X-Write-Version."""

    def __init__(
        self,
        outbox_repository: OutboxRepository,
        entries: Sequence[OutboxEntry],
    ) -> None:
        super().__init__()
        self._outbox_repository = outbox_repository
        self._entries: list[OutboxEntry] = list(entries)

    async def forward(self) -> int:
        async with aatomic():
            for entry in self._entries:
                sequence = await self._outbox_repository.append(entry)
                self._appended_sequences.append(sequence)

        return self.last_appended_sequence

    async def compensate(self) -> None:
        raise NotImplementedError(
            "OutboxEmissionStep compensation should never be called — it is the final step."
        )

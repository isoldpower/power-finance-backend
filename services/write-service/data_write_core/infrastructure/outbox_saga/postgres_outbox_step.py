from abc import abstractmethod
from collections.abc import Sequence

from saga_pattern_py import SagaStep

from data_write_core.application.db_utils import aatomic
from data_write_core.application.interfaces import OutboxRepository
from data_write_core.domain.value_objects import OutboxEntry


class OutboxSagaStep(SagaStep[int]):
    """SAGA step whose forward() appends outbox entries and records their
    sequence numbers. `last_appended_sequence` exposes the latest (surfaced
    as X-Write-Version)."""

    def __init__(self) -> None:
        self._appended_sequences: list[int] = []

    @abstractmethod
    async def forward(self) -> int:
        raise NotImplementedError()

    @property
    def last_appended_sequence(self) -> int:
        if not self._appended_sequences:
            raise RuntimeError(
                "OutboxSagaStep.last_appended_sequence read before forward() completed",
            )

        return self._appended_sequences[-1]


class PostgresOutboxEmissionStep(OutboxSagaStep):
    """Final saga step. Appends outbox entries; last_appended_sequence
    is returned as X-Write-Version."""

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

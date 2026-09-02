from abc import ABC

from data_write_core.infrastructure.outbox_saga import (
    FinalizedSagaCoordinator,
    PostgresAction,
    PostgresOutboxEmissionStep,
    PostgresWriteStep,
)

from ...bootstrap import get_repository_registry
from ...dtos import AutomationDTO
from ...interfaces import AutomationRepository, OutboxRepository
from ..command_base import CommandHandlerBase


class AutomationCommandHandler(CommandHandlerBase[AutomationDTO], ABC):
    def __init__(
        self,
        automation_repository: AutomationRepository | None = None,
        outbox_repository: OutboxRepository | None = None,
    ) -> None:
        if automation_repository is None or outbox_repository is None:
            registry = get_repository_registry()
            automation_repository = automation_repository or registry.automation_repository
            outbox_repository = outbox_repository or registry.outbox_repository

        self._automation_repository = automation_repository
        self._outbox_repository = outbox_repository

    async def _run_saga(
        self,
        write: PostgresAction,
        undo: PostgresAction,
        entries: list,
    ) -> int:
        saga_coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                PostgresWriteStep(
                    forward_action=write,
                    compensate_action=undo,
                ),
            ],
            final_step=PostgresOutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                entries=entries,
            ),
        )

        return await saga_coordinator.run_transaction()

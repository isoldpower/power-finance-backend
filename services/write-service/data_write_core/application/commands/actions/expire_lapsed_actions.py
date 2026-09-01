from dataclasses import dataclass
from datetime import UTC, datetime

from data_write_core.domain.entities import ActionEntity
from data_write_core.infrastructure.outbox_saga import (
    FinalizedSagaCoordinator,
    PostgresOutboxEmissionStep,
    PostgresWriteStep,
)

from ...bootstrap import get_repository_registry
from ...interfaces import ActionRepository, OutboxRepository
from ._events import action_resolved

DEFAULT_SWEEP_LIMIT = 200


@dataclass(frozen=True)
class ExpireLapsedActionsCommand:
    limit: int = DEFAULT_SWEEP_LIMIT
    now: datetime | None = None


class ExpireLapsedActionsCommandHandler:
    def __init__(
        self,
        action_repository: ActionRepository | None = None,
        outbox_repository: OutboxRepository | None = None,
    ) -> None:
        if action_repository is None or outbox_repository is None:
            registry = get_repository_registry()
            action_repository = action_repository or registry.action_repository
            outbox_repository = outbox_repository or registry.outbox_repository

        self._action_repository = action_repository
        self._outbox_repository = outbox_repository

    async def handle(self, command: ExpireLapsedActionsCommand) -> list[str]:
        timestamp_now = command.now or datetime.now(UTC)
        lapsed = await self._action_repository.find_lapsed_pending(
            timestamp_now,
            command.limit,
        )

        expired_actions: list[str] = []
        for action in lapsed:
            action.expire(timestamp_now)
            await self._sweep_one(action, timestamp_now)
            expired_actions.append(action.unique_id)

        return expired_actions

    async def _sweep_one(self, action: ActionEntity, now: datetime) -> None:
        async def write() -> None:
            await self._action_repository.save_action(action)

        async def undo() -> None:
            await self._action_repository.save_action(action)

        saga_coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                PostgresWriteStep(
                    forward_action=write,
                    compensate_action=undo,
                ),
            ],
            final_step=PostgresOutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                entries=[action_resolved(action, at=now)],
            ),
        )

        await saga_coordinator.run_transaction()

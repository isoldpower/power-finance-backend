from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from data_write_core.domain.entities import ActionEntity
from data_write_core.domain.exceptions import (
    ActionAlreadyResolvedError,
    UnknownResolutionError,
)
from data_write_core.infrastructure.outbox_saga import (
    FinalizedSagaCoordinator,
    PostgresOutboxEmissionStep,
    PostgresWriteStep,
)

from ...bootstrap import get_repository_registry
from ...dtos import ActionDTO, action_to_dto
from ...interfaces import ActionRepository, OutboxRepository
from ..command_base import CommandHandlerBase
from ._events import action_resolved


@dataclass(frozen=True)
class ResolveActionCommand:
    user_id: int
    user_external_id: str
    action_id: UUID
    resolution_id: str


@dataclass(frozen=True)
class ResolvedAction:
    action: ActionDTO
    applies: bool


class ResolveActionCommandHandler(CommandHandlerBase[ResolvedAction]):
    _action_repository: ActionRepository
    _outbox_repository: OutboxRepository

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

    async def handle(self, command: ResolveActionCommand) -> tuple[ResolvedAction, int]:
        action = await self._action_repository.get_user_action_by_id(
            command.action_id,
            command.user_id,
        )
        if action.is_answered:
            raise ActionAlreadyResolvedError(command.action_id)

        resolution = action.resolution_by_id(command.resolution_id)
        if resolution is None:
            raise UnknownResolutionError(command.resolution_id)

        resolved_at = datetime.now(UTC)
        action.resolve(resolution, resolved_at)
        stored, write_version = await self._run_saga(action, command, resolved_at)

        return (
            ResolvedAction(
                action=action_to_dto(stored),
                applies=resolution.applies,
            ),
            write_version,
        )

    async def _run_saga(
        self,
        action: ActionEntity,
        command: ResolveActionCommand,
        resolved_at: datetime,
    ) -> tuple[ActionEntity, int]:
        holder: dict[str, ActionEntity] = {}
        answered = await self._action_repository.get_user_action_by_id(
            command.action_id,
            command.user_id,
        )

        async def write() -> None:
            holder["action"] = await self._action_repository.save_action(action)

        async def undo() -> None:
            await self._action_repository.save_action(answered)

        saga_coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                PostgresWriteStep(
                    forward_action=write,
                    compensate_action=undo,
                ),
            ],
            final_step=PostgresOutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                entries=[action_resolved(action, at=resolved_at)],
            ),
        )
        write_version = await saga_coordinator.run_transaction()

        return holder.get("action", action), write_version

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from data_write_core.domain.entities import ActionEntity, ActionSeverity
from data_write_core.domain.value_objects import ActionResolution
from data_write_core.infrastructure.outbox_saga import (
    FinalizedSagaCoordinator,
    PostgresAction,
    PostgresOutboxEmissionStep,
    PostgresWriteStep,
)

from ...bootstrap import get_repository_registry
from ...dtos import ActionDTO, action_to_dto
from ...interfaces import ActionRepository, OutboxRepository
from ..command_base import CommandHandlerBase
from ._events import action_raised


@dataclass(frozen=True)
class RaiseActionCommand:
    user_id: int
    user_external_id: str
    source: str
    kind: str
    title: str
    body: str = ""
    severity: str = ActionSeverity.INFO
    subject_type: str | None = None
    subject_id: str | None = None
    money_amount: Decimal | None = None
    money_currency: str | None = None
    group_key: str | None = None
    expires_at: datetime | None = None
    resolutions: tuple[ActionResolution, ...] = field(default_factory=tuple)


class EmptyResolutionsError(ValueError):
    pass


class RaiseActionCommandHandler(CommandHandlerBase[ActionDTO]):
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

    async def handle(self, command: RaiseActionCommand) -> tuple[ActionDTO, int]:
        if not command.resolutions:
            raise EmptyResolutionsError(command.kind)

        now = datetime.now(UTC)
        existing = await self._existing_for(command)
        if existing is not None:
            return await self._collapse_onto(existing, command, now)

        return await self._create(self._build(command, now), command)

    async def _existing_for(self, command: RaiseActionCommand) -> ActionEntity | None:
        if not command.group_key:
            return None

        return await self._action_repository.find_pending_by_group_key(
            command.user_id,
            command.group_key,
        )

    def _build(self, command: RaiseActionCommand, now: datetime) -> ActionEntity:
        return ActionEntity(
            id=str(uuid4()),
            user_id=str(command.user_id),
            user_external_id=command.user_external_id,
            source=command.source,
            kind=command.kind,
            severity=command.severity,
            title=command.title,
            body=command.body,
            subject_type=command.subject_type,
            subject_id=command.subject_id,
            money_amount=command.money_amount,
            money_currency=command.money_currency,
            group_key=command.group_key,
            expires_at=command.expires_at,
            resolutions=command.resolutions,
            created_at=now,
            last_seen_at=now,
        )

    async def _create(
        self,
        action: ActionEntity,
        command: RaiseActionCommand,
    ) -> tuple[ActionDTO, int]:
        holder: dict[str, ActionEntity] = {}

        async def write() -> None:
            holder["action"] = await self._action_repository.create_action(action)

        async def undo() -> None:
            await self._action_repository.hard_delete_action(UUID(action.unique_id))

        return await self._run_saga(action, command, write, undo, holder)

    async def _collapse_onto(
        self,
        existing: ActionEntity,
        command: RaiseActionCommand,
        now: datetime,
    ) -> tuple[ActionDTO, int]:
        previous_occurrences = existing.occurrences
        previous_last_seen_at = existing.last_seen_at
        previous_updated_at = existing.updated_at
        existing.observe_again(now)
        holder: dict[str, ActionEntity] = {}

        async def write() -> None:
            holder["action"] = await self._action_repository.save_action(existing)

        async def undo() -> None:
            existing.restore_observation(
                previous_occurrences,
                previous_last_seen_at,
                previous_updated_at,
            )
            await self._action_repository.save_action(existing)

        return await self._run_saga(
            existing,
            command,
            write,
            undo,
            holder,
        )

    async def _run_saga(
        self,
        action: ActionEntity,
        command: RaiseActionCommand,
        write: PostgresAction,
        undo: PostgresAction,
        holder: dict[str, ActionEntity],
    ) -> tuple[ActionDTO, int]:
        saga_coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                PostgresWriteStep(
                    forward_action=write,
                    compensate_action=undo,
                ),
            ],
            final_step=PostgresOutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                entries=[action_raised(action)],
            ),
        )
        write_version = await saga_coordinator.run_transaction()

        return (
            action_to_dto(holder.get("action", action)),
            write_version,
        )

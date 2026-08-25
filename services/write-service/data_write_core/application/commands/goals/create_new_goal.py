from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from kafka_messages import GoalCreated

from data_write_core.domain.entities import GoalEntity
from data_write_core.domain.exceptions import UnsupportedCurrencyError
from data_write_core.domain.value_objects import GoalData
from data_write_core.infrastructure.messaging import (
    build_outbox_entry,
    datetime_to_timestamp,
)
from data_write_core.infrastructure.outbox_saga import (
    FinalizedSagaCoordinator,
    PostgresAction,
    PostgresOutboxEmissionStep,
    PostgresWriteStep,
)

from ..._amount_scale import ensure_amount_scale
from ...bootstrap import get_repository_registry
from ...dtos import GoalDTO, goal_to_dto
from ...interfaces import (
    CurrencyRepository,
    GoalRepository,
    OutboxRepository,
)
from ..command_base import CommandHandlerBase


@dataclass(frozen=True)
class CreateNewGoalCommand:
    user_id: int
    user_external_id: str
    name: str
    currency: str
    target: Decimal
    finish_at: datetime | None = None


class CreateNewGoalCommandHandler(CommandHandlerBase[GoalDTO]):
    _goal_repository: GoalRepository
    _currency_repository: CurrencyRepository
    _outbox_repository: OutboxRepository

    def __init__(
        self,
        goal_repository: GoalRepository | None = None,
        currency_repository: CurrencyRepository | None = None,
        outbox_repository: OutboxRepository | None = None,
    ) -> None:
        registry = get_repository_registry()
        self._goal_repository = goal_repository or registry.goal_repository
        self._currency_repository = currency_repository or registry.currency_repository
        self._outbox_repository = outbox_repository or registry.outbox_repository

    async def handle(self, command: CreateNewGoalCommand) -> tuple[GoalDTO, int]:
        currency_code = command.currency.upper()
        if not await self._currency_repository.currency_code_exists(currency_code):
            raise UnsupportedCurrencyError(currency_code)

        await ensure_amount_scale(command.target, currency_code)

        timestamp_now = datetime.now()
        new_goal = GoalEntity.create(
            id=str(uuid4()),
            data=GoalData(
                title=command.name,
                currency_code=currency_code,
                target=command.target,
                finish_at=command.finish_at,
            ),
            user_id=str(command.user_id),
            created_at=timestamp_now,
        )

        persisted_goal, write_version = await self._run_saga(
            new_goal,
            partition_key=command.user_external_id,
        )

        return (
            goal_to_dto(persisted_goal, progress=Decimal("0")),
            write_version,
        )

    async def _run_saga(
        self,
        new_goal: GoalEntity,
        partition_key: str,
    ) -> tuple[GoalEntity, int]:
        created_goal_holder: dict[str, GoalEntity] = {}
        persist_goal, undo_persisted_goal = self._get_save_unsave_lambdas(
            goal_holder=created_goal_holder,
            created_goal=new_goal,
        )

        saga_coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                PostgresWriteStep(
                    forward_action=persist_goal,
                    compensate_action=undo_persisted_goal,
                ),
            ],
            final_step=PostgresOutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                entries=[
                    build_outbox_entry(
                        GoalCreated(
                            goal_id=new_goal.unique_id,
                            user_id=int(new_goal.user_id),
                            title=new_goal.title,
                            currency_code=new_goal.currency_code,
                            target=str(new_goal.target),
                            created_at=datetime_to_timestamp(new_goal.created_at),
                            finish_at=(
                                datetime_to_timestamp(new_goal.finish_at)
                                if new_goal.finish_at
                                else None
                            ),
                            url=new_goal.url or "",
                        ),
                        aggregate_type="goal",
                        aggregate_id=new_goal.unique_id,
                        partition_key=partition_key,
                    )
                ],
            ),
        )

        outbox_version = await saga_coordinator.run_transaction()
        return created_goal_holder["goal"], outbox_version

    def _get_save_unsave_lambdas(
        self,
        goal_holder: dict[str, GoalEntity],
        created_goal: GoalEntity,
    ) -> tuple[PostgresAction, PostgresAction]:
        async def persist_goal() -> None:
            goal_holder["goal"] = await self._goal_repository.create_goal(created_goal)

        async def undo_persisted_goal() -> None:
            await self._goal_repository.hard_delete_goal(UUID(created_goal.unique_id))

        return persist_goal, undo_persisted_goal

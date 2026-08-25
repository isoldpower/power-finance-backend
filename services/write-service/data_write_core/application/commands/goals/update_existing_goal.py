from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from kafka_messages import GoalUpdated

from data_write_core.domain.aggregates import GoalAggregate
from data_write_core.domain.entities import GoalEntity
from data_write_core.domain.entities.goal import UNCHANGED
from data_write_core.domain.value_objects import GoalData
from data_write_core.infrastructure.messaging import build_outbox_entry, datetime_to_timestamp
from data_write_core.infrastructure.outbox_saga import (
    FinalizedSagaCoordinator,
    PostgresAction,
    PostgresOutboxEmissionStep,
    PostgresWriteStep,
)

from ..._amount_scale import ensure_amount_scale
from ...bootstrap import get_repository_registry
from ...dtos import GoalDTO, goal_to_dto
from ...interfaces import GoalRepository, MoneyFlowRepository, OutboxRepository
from ..command_base import CommandHandlerBase
from ._goal_loader import LoadGoalMixin


@dataclass(frozen=True)
class UpdateExistingGoalCommand:
    user_id: int
    user_external_id: str
    goal_id: UUID
    new_name: str | object = UNCHANGED
    target: Decimal | object = UNCHANGED
    finish_at: datetime | None | object = UNCHANGED
    url: str | None | object = UNCHANGED


class UpdateExistingGoalCommandHandler(CommandHandlerBase[GoalDTO], LoadGoalMixin):
    _goal_repository: GoalRepository
    _outbox_repository: OutboxRepository

    def __init__(
        self,
        goal_repository: GoalRepository | None = None,
        money_flow_repository: MoneyFlowRepository | None = None,
        outbox_repository: OutboxRepository | None = None,
    ) -> None:
        registry = get_repository_registry()
        goal_repository = goal_repository or registry.goal_repository
        money_flow_repository = money_flow_repository or registry.money_flow_repository
        outbox_repository = outbox_repository or registry.outbox_repository

        LoadGoalMixin.__init__(self, goal_repository, money_flow_repository)

        self._goal_repository = goal_repository
        self._outbox_repository = outbox_repository

    async def handle(self, command: UpdateExistingGoalCommand) -> tuple[GoalDTO, int]:
        goal_aggregate = await self.load_goal_aggregate(
            goal_id=command.goal_id,
            user_id=command.user_id,
        )

        if isinstance(command.target, Decimal):
            await ensure_amount_scale(
                command.target,
                goal_aggregate.root.currency_code,
            )

        timestamp_now = datetime.now()
        previous_state = goal_aggregate.root.snapshot()
        goal_aggregate.update_metadata(
            now=timestamp_now,
            title=command.new_name,
            target=command.target,
            finish_at=command.finish_at,
            url=command.url,
        )
        updated_goal, latest_sequence = await self._run_saga(
            goal_aggregate=goal_aggregate,
            previous_state=previous_state,
            timestamp=timestamp_now,
            partition_key=command.user_external_id,
        )
        goal_dto = goal_to_dto(
            updated_goal,
            progress=goal_aggregate.progress,
        )

        await self._publish_domain_events(goal_aggregate)
        return goal_dto, latest_sequence

    async def _run_saga(
        self,
        goal_aggregate: GoalAggregate,
        previous_state: GoalData,
        timestamp: datetime,
        partition_key: str,
    ) -> tuple[GoalEntity, int]:
        goal_holder: dict[str, GoalEntity] = {}
        persist_update, undo_update = self._get_save_unsave_lambdas(
            goal_holder=goal_holder,
            goal_aggregate=goal_aggregate,
            previous_state=previous_state,
        )

        root = goal_aggregate.root
        saga_coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                PostgresWriteStep(
                    forward_action=persist_update,
                    compensate_action=undo_update,
                ),
            ],
            final_step=PostgresOutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                entries=[
                    build_outbox_entry(
                        GoalUpdated(
                            goal_id=goal_aggregate.unique_id,
                            user_id=int(root.user_id),
                            previous_title=previous_state.title,
                            new_title=root.title,
                            updated_at=datetime_to_timestamp(timestamp),
                            target=str(root.target),
                            finish_at=(
                                datetime_to_timestamp(root.finish_at) if root.finish_at else None
                            ),
                            url=root.url or "",
                        ),
                        aggregate_type="goal",
                        aggregate_id=goal_aggregate.unique_id,
                        partition_key=partition_key,
                    )
                ],
            ),
        )

        latest_sequence = await saga_coordinator.run_transaction()
        return goal_holder["goal"], latest_sequence

    def _get_save_unsave_lambdas(
        self,
        goal_holder: dict[str, GoalEntity],
        goal_aggregate: GoalAggregate,
        previous_state: GoalData,
    ) -> tuple[PostgresAction, PostgresAction]:
        async def persist_update() -> None:
            goal_holder["goal"] = await self._goal_repository.save_goal(goal_aggregate.root)

        async def undo_update() -> None:
            goal_aggregate.root.apply(previous_state, datetime.now())
            await self._goal_repository.save_goal(goal_aggregate.root)

        return persist_update, undo_update

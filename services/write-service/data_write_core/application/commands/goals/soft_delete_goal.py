from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from kafka_messages import GoalDeleted

from data_write_core.domain.aggregates import GoalAggregate
from data_write_core.domain.entities import GoalEntity
from data_write_core.infrastructure.messaging import build_outbox_entry, datetime_to_timestamp
from data_write_core.infrastructure.outbox_saga import (
    FinalizedSagaCoordinator,
    PostgresAction,
    PostgresOutboxEmissionStep,
    PostgresWriteStep,
)

from ...bootstrap import get_repository_registry
from ...dtos import GoalDTO, goal_to_dto
from ...interfaces import GoalRepository, MoneyFlowRepository, OutboxRepository
from ..command_base import CommandHandlerBase
from ._goal_loader import LoadGoalMixin


@dataclass(frozen=True)
class SoftDeleteGoalCommand:
    user_id: int
    user_external_id: str
    goal_id: UUID


class SoftDeleteGoalCommandHandler(CommandHandlerBase[GoalDTO], LoadGoalMixin):
    """Closing a goal, not deleting it."""

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

    async def handle(self, command: SoftDeleteGoalCommand) -> tuple[GoalDTO, int]:
        goal_aggregate = await self.load_goal_aggregate(
            goal_id=command.goal_id,
            user_id=command.user_id,
        )

        timestamp_now = datetime.now()
        goal_aggregate.soft_delete(now=timestamp_now)
        saved_goal, latest_sequence = await self._run_saga(
            goal_aggregate=goal_aggregate,
            timestamp_now=timestamp_now,
            partition_key=command.user_external_id,
        )
        goal_dto = goal_to_dto(
            saved_goal,
            progress=goal_aggregate.progress,
        )

        await self._publish_domain_events(goal_aggregate)
        return goal_dto, latest_sequence

    async def _run_saga(
        self,
        goal_aggregate: GoalAggregate,
        timestamp_now: datetime,
        partition_key: str,
    ) -> tuple[GoalEntity, int]:
        saved_goal_holder: dict[str, GoalEntity] = {}
        persist_soft_delete, undo_soft_delete = self._get_save_unsave_lambdas(
            goal_holder=saved_goal_holder,
            goal_aggregate=goal_aggregate,
        )

        saga_coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                PostgresWriteStep(
                    forward_action=persist_soft_delete,
                    compensate_action=undo_soft_delete,
                ),
            ],
            final_step=PostgresOutboxEmissionStep(
                outbox_repository=self._outbox_repository,
                entries=[
                    build_outbox_entry(
                        GoalDeleted(
                            goal_id=goal_aggregate.unique_id,
                            user_id=int(goal_aggregate.root.user_id),
                            deleted_at=datetime_to_timestamp(timestamp_now),
                        ),
                        aggregate_type="goal",
                        aggregate_id=goal_aggregate.unique_id,
                        partition_key=partition_key,
                    )
                ],
            ),
        )

        latest_sequence = await saga_coordinator.run_transaction()
        return saved_goal_holder["goal"], latest_sequence

    def _get_save_unsave_lambdas(
        self,
        goal_holder: dict[str, GoalEntity],
        goal_aggregate: GoalAggregate,
    ) -> tuple[PostgresAction, PostgresAction]:
        async def persist_soft_delete() -> None:
            goal_holder["goal"] = await self._goal_repository.save_goal(goal_aggregate.root)

        async def undo_soft_delete() -> None:
            goal_aggregate.root.restore(datetime.now())
            await self._goal_repository.save_goal(goal_aggregate.root)

        return persist_soft_delete, undo_soft_delete

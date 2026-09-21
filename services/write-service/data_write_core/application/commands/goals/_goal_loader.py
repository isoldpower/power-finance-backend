from uuid import UUID

from data_write_core.domain.aggregates import GoalAggregate

from ...interfaces import GoalRepository, MoneyFlowRepository


class LoadGoalMixin:
    def __init__(
        self,
        goal_repository: GoalRepository,
        money_flow_repository: MoneyFlowRepository,
    ) -> None:
        self._goal_flow_repository = money_flow_repository
        self._loading_goal_repository = goal_repository

    async def load_goal_aggregate(self, goal_id: UUID, user_id: int) -> GoalAggregate:
        goal_entity = await self._loading_goal_repository.get_user_goal_by_id(
            goal_id=goal_id,
            user_id=user_id,
        )
        checkpoint = await self._goal_flow_repository.get_checkpoint(goal_id)
        settled_at = checkpoint.created_at.isoformat() if checkpoint else None
        unsettled_flows = await self._goal_flow_repository.get_unsettled_flows(
            goal_id,
            settled_at,
        )

        return GoalAggregate(
            goal_entity=goal_entity,
            unsettled_flows=unsettled_flows,
            balance_checkpoint=checkpoint,
        )

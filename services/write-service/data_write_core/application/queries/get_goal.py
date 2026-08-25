from dataclasses import dataclass
from uuid import UUID

from ..bootstrap import get_repository_registry
from ..dtos import GoalDTO, goal_to_dto
from ..interfaces import GoalRepository, MoneyFlowRepository
from ._goal_progress import load_goal_progress


@dataclass(frozen=True)
class GetFallbackGoalQuery:
    user_id: int
    goal_id: UUID


class GetFallbackGoalQueryHandler:
    def __init__(
        self,
        goal_repository: GoalRepository | None = None,
        money_flow_repository: MoneyFlowRepository | None = None,
    ) -> None:
        if goal_repository is None or money_flow_repository is None:
            registry = get_repository_registry()
            goal_repository = goal_repository or registry.goal_repository
            money_flow_repository = money_flow_repository or registry.money_flow_repository

        self._goal_repository = goal_repository
        self._money_flow_repository = money_flow_repository

    async def handle(self, query: GetFallbackGoalQuery) -> GoalDTO:
        goal = await self._goal_repository.get_user_goal_by_id(
            goal_id=query.goal_id,
            user_id=query.user_id,
        )
        progress = await load_goal_progress(goal, self._money_flow_repository)

        return goal_to_dto(goal, progress=progress)

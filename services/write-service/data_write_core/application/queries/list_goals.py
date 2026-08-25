import asyncio
from dataclasses import dataclass

from write_service.common.pagination import PageRequest

from data_write_core.domain.entities import GoalEntity

from ..bootstrap import get_repository_registry
from ..dtos import GoalDTO, goal_to_dto
from ..interfaces import GoalRepository, MoneyFlowRepository
from ._goal_progress import load_goal_progress


@dataclass(frozen=True)
class ListFallbackGoalsQuery:
    user_id: int
    page: PageRequest


class ListFallbackGoalsQueryHandler:
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

    async def handle(self, query: ListFallbackGoalsQuery) -> tuple[list[GoalDTO], int]:
        goals = await self._goal_repository.get_user_goals(
            user_id=query.user_id,
            page=query.page,
        )
        # Gathered positionally rather than from a splatted list: the splat makes
        # both results one joined type, which is how `total, *goal_dtos` came to
        # unpack the page into a list holding a list.
        total, goal_dtos = await asyncio.gather(
            self._goal_repository.count_user_goals(query.user_id),
            asyncio.gather(*(self._load_goal_dto(goal) for goal in goals)),
        )

        return list(goal_dtos), total

    async def _load_goal_dto(self, goal: GoalEntity) -> GoalDTO:
        progress = await load_goal_progress(
            goal,
            self._money_flow_repository,
        )

        return goal_to_dto(goal, progress=progress)

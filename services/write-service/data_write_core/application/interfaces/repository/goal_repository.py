from abc import ABC, abstractmethod
from uuid import UUID

from write_service.common.pagination import PageRequest

from data_write_core.domain.entities import GoalEntity


class GoalRepository(ABC):
    @abstractmethod
    async def create_goal(self, goal: GoalEntity) -> GoalEntity:
        raise NotImplementedError()

    @abstractmethod
    async def get_user_goal_by_id(self, goal_id: UUID, user_id: int) -> GoalEntity:
        raise NotImplementedError()

    @abstractmethod
    async def get_user_goals(
        self,
        user_id: int,
        page: PageRequest | None = None,
    ) -> list[GoalEntity]:
        raise NotImplementedError()

    @abstractmethod
    async def count_user_goals(self, user_id: int) -> int:
        raise NotImplementedError()

    @abstractmethod
    async def get_user_goal_for_update(self, goal_id: UUID, user_id: int) -> GoalEntity:
        raise NotImplementedError()

    @abstractmethod
    async def save_goal(self, goal: GoalEntity) -> GoalEntity:
        raise NotImplementedError()

    @abstractmethod
    async def hard_delete_goal(self, goal_id: UUID) -> None:
        raise NotImplementedError()

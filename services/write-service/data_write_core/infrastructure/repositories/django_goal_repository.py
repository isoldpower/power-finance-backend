from uuid import UUID

from write_service.common.pagination import CREATED_AT_DESC, PageRequest, apply_keyset

from data_write_core.application.interfaces import GoalRepository
from data_write_core.domain.entities import GoalEntity

from ..orm import GoalModel
from .mappers import GoalMapper


class DjangoGoalRepository(GoalRepository):
    async def create_goal(self, goal: GoalEntity) -> GoalEntity:
        created_goal = GoalModel()
        GoalMapper.apply_to_model(created_goal, goal)

        await created_goal.asave()
        refreshed_goal = await GoalModel.objects.select_related("currency").aget(id=created_goal.id)

        return GoalMapper.to_domain(refreshed_goal)

    async def get_user_goal_by_id(self, goal_id: UUID, user_id: int) -> GoalEntity:
        requested_goal: GoalModel = await (
            GoalModel.objects.with_deleted()
            .select_related("currency")
            .aget(id=goal_id, user_id=user_id)
        )

        return GoalMapper.to_domain(requested_goal)

    async def get_user_goals(
        self,
        user_id: int,
        page: PageRequest | None = None,
    ) -> list[GoalEntity]:
        queryset = GoalModel.objects.select_related("currency").filter(user_id=user_id)
        goal_rows = (
            apply_keyset(queryset, page)
            if page
            else queryset.order_by(*CREATED_AT_DESC.django_ordering)
        )

        return [GoalMapper.to_domain(goal) async for goal in goal_rows]

    async def count_user_goals(self, user_id: int) -> int:
        return await GoalModel.objects.filter(user_id=user_id).acount()

    async def get_user_goal_for_update(self, goal_id: UUID, user_id: int) -> GoalEntity:
        requested_goal: GoalModel = await (
            GoalModel.objects.with_deleted()
            .select_for_update()
            .select_related("currency")
            .aget(id=goal_id, user_id=user_id)
        )

        return GoalMapper.to_domain(requested_goal)

    async def save_goal(self, goal: GoalEntity) -> GoalEntity:
        requested_goal = await (
            GoalModel.objects.with_deleted().select_related("currency").aget(id=goal.unique_id)
        )

        GoalMapper.apply_to_model(requested_goal, goal)
        await requested_goal.asave()

        return GoalMapper.to_domain(requested_goal)

    async def hard_delete_goal(self, goal_id: UUID) -> None:
        await GoalModel.objects.with_deleted().filter(id=goal_id).adelete()

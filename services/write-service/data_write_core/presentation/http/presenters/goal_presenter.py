from write_service.common.timestamps import to_iso

from data_write_core.application.dtos import GoalDTO
from data_write_core.application.money_scales import money_at_scale


class GoalHttpPresenter:
    @staticmethod
    async def present_one(goal: GoalDTO) -> dict:
        return {
            "id": str(goal.id),
            "name": goal.name,
            "url": goal.url,
            "currency": goal.currency,
            "finish_at": to_iso(goal.finish_at),
            "created_at": to_iso(goal.created_at),
            "updated_at": to_iso(goal.updated_at),
            "deleted_at": to_iso(goal.deleted_at),
            "target": await money_at_scale(goal.target, goal.currency),
            "progress": await money_at_scale(goal.progress, goal.currency),
        }

    @staticmethod
    async def present_many(goals: list[GoalDTO]) -> list[dict]:
        return [await GoalHttpPresenter.present_one(goal) for goal in goals]

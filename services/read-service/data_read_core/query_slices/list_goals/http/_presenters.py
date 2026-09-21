from data_read_core.shared.money import money_at_scale
from data_read_core.shared.pagination import Page

from ..dtos import GoalDTO


async def present_one(goal: GoalDTO) -> dict:
    return {
        "id": goal.id,
        "name": goal.name,
        "url": goal.url,
        "currency": goal.currency,
        "finish_at": goal.finish_at,
        "created_at": goal.created_at,
        "updated_at": goal.updated_at,
        "deleted_at": goal.deleted_at,
        "target": await money_at_scale(
            goal.target_amount,
            goal.currency,
        ),
        "progress": await money_at_scale(
            goal.progress_amount,
            goal.currency,
        ),
    }


def present_meta(
    page: Page,
    cached: bool,
) -> dict:
    return page.meta(cached=cached)


async def present_many(goals: list[GoalDTO]) -> list[dict]:
    return [await present_one(goal) for goal in goals]

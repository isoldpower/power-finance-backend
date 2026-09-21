from data_read_core.shared.pagination import PageRequest, apply_keyset
from data_read_core.shared.postgres_orm import GoalReadModel


def _owned_queryset(user_id: int):
    return GoalReadModel.objects.filter(
        user_id=user_id,
        deleted_at__isnull=True,
    )


async def fetch_owned_goals(
    user_id: int,
    page: PageRequest,
) -> list[GoalReadModel]:
    queryset = apply_keyset(
        _owned_queryset(user_id),
        page,
    )

    return [goal async for goal in queryset]


async def count_owned_goals(user_id: int) -> int:
    return await _owned_queryset(user_id).acount()

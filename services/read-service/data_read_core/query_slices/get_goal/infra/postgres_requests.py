from data_read_core.shared.pagination import PageRequest, apply_keyset
from data_read_core.shared.postgres_orm import (
    GoalReadModel,
    MoneyContainers,
    TransactionReadModel,
)


async def fetch_owned_goal(user_id: int, goal_id: str) -> GoalReadModel | None:
    return await GoalReadModel.objects.filter(
        id=goal_id,
        user_id=user_id,
    ).afirst()


def history_queryset(goal_id: str):
    return TransactionReadModel.objects.filter(
        wallet_id=goal_id,
        container_kind=MoneyContainers.GOAL,
        deleted_at__isnull=True,
    )


async def fetch_goal_history(
    goal_id: str,
    page: PageRequest,
) -> list[TransactionReadModel]:
    queryset = apply_keyset(history_queryset(goal_id), page)

    return [transaction async for transaction in queryset]


async def count_goal_history(goal_id: str) -> int:
    return await history_queryset(goal_id).acount()

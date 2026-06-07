from data_read_core.shared.postgres_orm import TransactionReadModel


async def fetch_user_transactions(
    user_id: int,
    limit: int,
    offset: int,
) -> list[TransactionReadModel]:
    queryset = TransactionReadModel.objects.filter(user_id=user_id).order_by("-occurred_at")[
        offset : offset + limit
    ]

    return [transaction async for transaction in queryset]


async def count_user_transactions(user_id: int) -> int:
    return await TransactionReadModel.objects.filter(user_id=user_id).acount()

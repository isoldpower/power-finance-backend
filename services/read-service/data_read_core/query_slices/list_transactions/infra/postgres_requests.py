from data_read_core.shared.pagination import PageRequest, apply_keyset
from data_read_core.shared.postgres_orm import TransactionReadModel


def _owned_queryset(user_id: int):
    return TransactionReadModel.objects.filter(
        user_id=user_id,
        deleted_at__isnull=True,
    )


async def fetch_user_transactions(
    user_id: int,
    page: PageRequest,
) -> list[TransactionReadModel]:
    queryset = apply_keyset(
        _owned_queryset(user_id),
        page,
    )

    return [transaction async for transaction in queryset]


async def count_user_transactions(user_id: int) -> int:
    return await _owned_queryset(user_id).acount()

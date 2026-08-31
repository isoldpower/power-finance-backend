from data_read_core.shared.pagination import PageRequest, apply_keyset
from data_read_core.shared.postgres_orm import AccountReadModel


def _owned_queryset(user_id: int):
    return AccountReadModel.objects.filter(user_id=user_id)


async def fetch_owned_accounts(
    user_id: int,
    page: PageRequest,
) -> list[AccountReadModel]:
    queryset = apply_keyset(
        _owned_queryset(user_id),
        page,
    )

    return [account async for account in queryset]


async def count_owned_accounts(user_id: int) -> int:
    return await _owned_queryset(user_id).acount()

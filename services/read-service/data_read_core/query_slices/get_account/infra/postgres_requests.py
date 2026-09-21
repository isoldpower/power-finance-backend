from data_read_core.shared.pagination import PageRequest, apply_keyset
from data_read_core.shared.postgres_orm import (
    AccountPostingReadModel,
    AccountReadModel,
)


async def fetch_owned_account(user_id: int, account_id: str) -> AccountReadModel | None:
    return await AccountReadModel.objects.filter(
        id=account_id,
        user_id=user_id,
    ).afirst()


def history_queryset(account_id: str):
    return AccountPostingReadModel.objects.filter(account_id=account_id)


async def fetch_account_history(
    account_id: str,
    page: PageRequest,
) -> list[AccountPostingReadModel]:
    queryset = apply_keyset(history_queryset(account_id), page)

    return [posting async for posting in queryset]


async def count_account_history(account_id: str) -> int:
    return await history_queryset(account_id).acount()

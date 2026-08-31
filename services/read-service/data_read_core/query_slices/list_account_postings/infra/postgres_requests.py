from data_read_core.shared.pagination import PageRequest, apply_keyset
from data_read_core.shared.postgres_orm import (
    AccountPostingReadModel,
    AccountReadModel,
)


async def account_is_owned(user_id: int, account_id: str) -> bool:
    return await AccountReadModel.objects.filter(
        id=account_id,
        user_id=user_id,
    ).aexists()


def _account_queryset(account_id: str):
    return AccountPostingReadModel.objects.filter(account_id=account_id)


async def fetch_account_postings(
    account_id: str,
    page: PageRequest,
) -> list[AccountPostingReadModel]:
    queryset = apply_keyset(
        _account_queryset(account_id),
        page,
    )

    return [posting async for posting in queryset]


async def count_account_postings(account_id: str) -> int:
    return await _account_queryset(account_id).acount()

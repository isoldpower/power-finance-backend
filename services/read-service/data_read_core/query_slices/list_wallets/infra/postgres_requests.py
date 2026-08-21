from data_read_core.shared.pagination import PageRequest, apply_keyset
from data_read_core.shared.postgres_orm import WalletReadModel


def _owned_queryset(user_id: int):
    return WalletReadModel.objects.filter(user_id=user_id)


async def fetch_owned_wallets(
    user_id: int,
    page: PageRequest,
) -> list[WalletReadModel]:
    """One page plus the lookahead row `build_page` needs to mint cursors."""

    queryset = apply_keyset(
        _owned_queryset(user_id),
        page,
    )

    return [wallet async for wallet in queryset]


async def count_owned_wallets(user_id: int) -> int:
    return await _owned_queryset(user_id).acount()

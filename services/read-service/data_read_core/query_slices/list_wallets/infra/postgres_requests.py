from data_read_core.shared.postgres_orm import WalletReadModel


async def fetch_owned_wallets(
    user_id: int,
    limit: int,
    offset: int,
) -> list[WalletReadModel]:
    queryset = WalletReadModel.objects.filter(user_id=user_id).order_by("-created_at")[
        offset : offset + limit
    ]

    return [wallet async for wallet in queryset]


async def count_owned_wallets(user_id: int) -> int:
    return await WalletReadModel.objects.filter(user_id=user_id).acount()

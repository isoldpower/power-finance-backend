from data_read_core.shared.postgres_orm import WalletReadModel


async def fetch_owned_wallet(user_id: int, wallet_id: str) -> WalletReadModel | None:
    return await WalletReadModel.objects.filter(
        id=wallet_id,
        user_id=user_id,
    ).afirst()

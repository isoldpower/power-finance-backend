from data_read_core.shared.money import money_at_scale

from ..dtos import WalletDTO


async def present_one(wallet: WalletDTO) -> dict:
    return {
        "id": wallet.id,
        "name": wallet.name,
        "balance": await money_at_scale(wallet.balance_amount, wallet.currency),
        "created_at": wallet.created_at,
        "updated_at": wallet.updated_at,
        "deleted_at": None,
    }


async def present_many(wallets: list[WalletDTO]) -> list[dict]:
    return [await present_one(wallet) for wallet in wallets]

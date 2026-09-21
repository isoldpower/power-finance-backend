from data_read_core.shared.money import money_at_scale

from ..dtos import WalletDTO


async def present_one(wallet: WalletDTO) -> dict:
    return {
        "id": wallet.id,
        "name": wallet.name,
        "created_at": wallet.created_at,
        "updated_at": wallet.updated_at,
        "deleted_at": wallet.deleted_at,
        "category": wallet.category,
        "currency": wallet.currency,
        "money": await money_at_scale(wallet.balance_amount, wallet.currency),
        "zero_balance": await money_at_scale(wallet.zero_balance_amount, wallet.currency),
        "favorite": wallet.favorite,
        "color": wallet.color,
    }


async def present_many(wallets: list[WalletDTO]) -> list[dict]:
    return [await present_one(wallet) for wallet in wallets]

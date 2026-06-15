from ..dtos import WalletDTO


def present_one(wallet: WalletDTO) -> dict:
    return {
        "id": wallet.id,
        "name": wallet.name,
        "balance": {
            "amount": wallet.balance_amount,
            "currency": wallet.currency,
        },
        "meta": {
            "id": wallet.id,
            "created_at": wallet.created_at,
            "updated_at": wallet.updated_at,
        },
    }


def present_many(wallets: list[WalletDTO]) -> list[dict]:
    return [present_one(wallet) for wallet in wallets]

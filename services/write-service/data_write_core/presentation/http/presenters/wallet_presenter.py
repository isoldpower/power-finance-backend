from data_write_core.application.dtos import WalletDTO


class WalletHttpPresenter:
    @staticmethod
    def present_one(wallet: WalletDTO) -> dict:
        return {
            "id": str(wallet.id),
            "name": wallet.name,
            "user_id": wallet.user_id,
            "balance": {
                "amount": str(wallet.balance_amount),
                "currency": wallet.currency,
            },
            "created_at": wallet.created_at,
            "updated_at": wallet.updated_at,
        }

    @staticmethod
    def present_many(wallets: list[WalletDTO]) -> list[dict]:
        return [WalletHttpPresenter.present_one(wallet) for wallet in wallets]

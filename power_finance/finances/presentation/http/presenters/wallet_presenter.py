from finances.application.dtos import WalletDTO


class WalletHttpPresenter:
    @staticmethod
    def present_meta(wallet: WalletDTO) -> dict:
        return {
            "id": wallet.id,
            "created_at": wallet.created_at,
            "updated_at": wallet.updated_at,
        }

    @staticmethod
    def present_one(wallet: WalletDTO) -> dict:
        return {
            "id": wallet.id,
            "name": wallet.name,
            "balance": {
                "amount": wallet.balance_amount,
                "currency": wallet.currency,
            },
            "meta": WalletHttpPresenter.present_meta(wallet),
        }

    @staticmethod
    def present_many(wallets: list[WalletDTO]) -> list[dict]:
        return [WalletHttpPresenter.present_one(wallet) for wallet in wallets]
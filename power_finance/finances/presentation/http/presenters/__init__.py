from finances.application.dtos import WalletDTO


class WalletHttpPresenter:
    @staticmethod
    def present_meta(wallet: WalletDTO) -> dict:
        return {
            "id": wallet.id,
            "created_at": wallet.created_at,
            "updated_at": wallet.updated_at,
        }

    @classmethod
    def present_one(cls, wallet: WalletDTO) -> dict:
        return {
            "id": wallet.id,
            "name": wallet.name,
            "credit": wallet.credit,
            "balance": {
                "amount": wallet.balance_amount,
                "currency": wallet.currency,
            },
            "meta": cls.present_meta(wallet),
        }

    @classmethod
    def present_many(cls, wallets: list[WalletDTO]) -> list[dict]:
        return [cls.present_one(wallet) for wallet in wallets]
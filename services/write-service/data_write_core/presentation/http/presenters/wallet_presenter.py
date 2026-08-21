from write_service.common.timestamps import to_iso

from data_write_core.application.dtos import WalletDTO
from data_write_core.application.money_scales import money_at_scale


class WalletHttpPresenter:
    @staticmethod
    async def present_one(wallet: WalletDTO) -> dict:
        return {
            "id": str(wallet.id),
            "name": wallet.name,
            "balance": await money_at_scale(
                wallet.balance_amount,
                wallet.currency,
            ),
            "created_at": to_iso(wallet.created_at),
            "updated_at": to_iso(wallet.updated_at),
            "deleted_at": None,
        }

    @staticmethod
    async def present_many(wallets: list[WalletDTO]) -> list[dict]:
        return [await WalletHttpPresenter.present_one(wallet) for wallet in wallets]

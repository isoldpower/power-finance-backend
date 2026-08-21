from write_service.common.timestamps import to_iso

from data_write_core.application.dtos import TransactionDTO, TransactionPlainDTO
from data_write_core.application.money_scales import amount_at_scale

from .wallet_presenter import WalletHttpPresenter


class TransactionHttpPresenter:
    @staticmethod
    async def present_one(transaction: TransactionDTO) -> dict:
        return {
            "id": str(transaction.id),
            "amount": await amount_at_scale(
                transaction.amount,
                transaction.currency_code,
            ),
            "currency": transaction.currency_code,
            "wallet": await WalletHttpPresenter.present_one(transaction.source_wallet),
            "cancels_other": (
                str(transaction.cancels_other) if transaction.cancels_other else None
            ),
            "adjusts_other": (
                str(transaction.adjusts_other) if transaction.adjusts_other else None
            ),
            "created_at": to_iso(transaction.created_at),
            "updated_at": None,
            "deleted_at": None,
        }

    @staticmethod
    async def present_many(transactions: list[TransactionPlainDTO]) -> list[dict]:
        return [
            {
                "id": str(transaction.id),
                "amount": await amount_at_scale(
                    transaction.amount,
                    transaction.currency_code,
                ),
                "currency": transaction.currency_code,
                "wallet_id": str(transaction.source_wallet_id),
                "cancels_other": (
                    str(transaction.cancels_other) if transaction.cancels_other else None
                ),
                "adjusts_other": (
                    str(transaction.adjusts_other) if transaction.adjusts_other else None
                ),
                "created_at": to_iso(transaction.created_at),
                "updated_at": None,
                "deleted_at": None,
            }
            for transaction in transactions
        ]

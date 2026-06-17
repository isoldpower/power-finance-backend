from data_write_core.application.dtos import TransactionDTO, TransactionPlainDTO

from .wallet_presenter import WalletHttpPresenter


class TransactionHttpPresenter:
    @staticmethod
    def present_one(transaction: TransactionDTO) -> dict:
        return {
            "id": str(transaction.id),
            "amount": str(transaction.amount),
            "currency_code": transaction.currency_code,
            "source_wallet": WalletHttpPresenter.present_one(transaction.source_wallet),
            "cancels_other": str(transaction.cancels_other) if transaction.cancels_other else None,
            "adjusts_other": str(transaction.adjusts_other) if transaction.adjusts_other else None,
            "created_at": transaction.created_at,
        }

    @staticmethod
    def present_many(transactions: list[TransactionPlainDTO]) -> list[dict]:
        return [
            {
                "id": str(transaction.id),
                "amount": str(transaction.amount),
                "currency_code": transaction.currency_code,
                "source_wallet_id": transaction.source_wallet_id,
                "cancels_other": str(transaction.cancels_other)
                if transaction.cancels_other
                else None,
                "adjusts_other": str(transaction.adjusts_other)
                if transaction.adjusts_other
                else None,
                "created_at": transaction.created_at,
            }
            for transaction in transactions
        ]

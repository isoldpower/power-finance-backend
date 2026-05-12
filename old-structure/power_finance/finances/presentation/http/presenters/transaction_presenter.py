from finances.application.dtos import TransactionDTO, TransactionPlainDTO
from .wallet_presenter import WalletHttpPresenter


class TransactionHttpPresenter:
    @staticmethod
    def present_one(transaction: TransactionDTO) -> dict:
        return {
            "id": transaction.id,
            "amount": transaction.amount,
            "currency_code": transaction.currency_code,
            "source_wallet": WalletHttpPresenter.present_one(transaction.source_wallet),
            "created_at": transaction.created_at,
        }

    @staticmethod
    def present_many(transactions: list[TransactionPlainDTO]) -> list[dict]:
        return [{
            "id": transaction.id,
            "amount": transaction.amount,
            "currency_code": transaction.currency_code,
            "source_wallet_id": transaction.source_wallet_id,
            "created_at": transaction.created_at,
        } for transaction in transactions]
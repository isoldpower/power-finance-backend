from finances.application.dtos import TransactionDTO, TransactionParticipantDTO
from finances.presentation.http.presenters import WalletHttpPresenter


class TransactionParticipantHttpPresenter:
    @staticmethod
    def present_detailed(transaction: TransactionParticipantDTO) -> dict:
        return {
            "wallet": WalletHttpPresenter.present_one(transaction.wallet),
            "amount": transaction.amount,
        }

    @staticmethod
    def present_preview(transaction: TransactionParticipantDTO) -> dict:
        return {
            "wallet_id": transaction.wallet.id,
            "amount": transaction.amount,
        }


class TransactionHttpPresenter:
    @staticmethod
    def present_meta(transaction: TransactionDTO) -> dict:
        return {
            "created_at": transaction.created_at,
            "id": transaction.id
        }

    @staticmethod
    def present_one(transaction: TransactionDTO) -> dict:
        return {
            "id": transaction.id,
            "from": TransactionParticipantHttpPresenter.present_detailed(transaction.sender),
            "to": TransactionParticipantHttpPresenter.present_detailed(transaction.receiver),
            "description": transaction.description,
            "meta": TransactionHttpPresenter.present_meta(transaction),
        }

    @staticmethod
    def present_many(transactions: list[TransactionDTO]) -> list[dict]:
        return [{
            "id": transaction.id,
            "from": TransactionParticipantHttpPresenter.present_preview(transaction.sender),
            "to": TransactionParticipantHttpPresenter.present_preview(transaction.receiver),
            "description": transaction.description,
            "meta": TransactionHttpPresenter.present_meta(transaction),
        } for transaction in transactions]
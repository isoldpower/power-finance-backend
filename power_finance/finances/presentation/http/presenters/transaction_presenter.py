from finances.application.dtos import (
    TransactionDTO,
    TransactionParticipantDTO,
    TransactionPlainDTO,
    TransactionParticipantPlainDTO
)
from .wallet_presenter import WalletHttpPresenter


class TransactionParticipantHttpPresenter:
    @staticmethod
    def present_detailed(transaction: TransactionParticipantDTO) -> dict:
        return {
            "wallet": WalletHttpPresenter.present_one(transaction.wallet),
            "amount": transaction.amount,
        }

    @staticmethod
    def present_preview(transaction: TransactionParticipantPlainDTO) -> dict:
        return {
            "wallet_id": transaction.wallet_id,
            "amount": transaction.amount,
        }


class TransactionHttpPresenter:
    @staticmethod
    def present_meta(transaction: TransactionDTO | TransactionPlainDTO) -> dict:
        return {
            "created_at": transaction.created_at,
            "id": transaction.id
        }

    @staticmethod
    def present_one(transaction: TransactionDTO) -> dict:
        return {
            "id": transaction.id,
            "type": transaction.type,
            "sender": TransactionParticipantHttpPresenter.present_detailed(
                transaction.sender
            ) if transaction.sender else None,
            "receiver": TransactionParticipantHttpPresenter.present_detailed(
                transaction.receiver
            ) if transaction.receiver else None,
            "description": transaction.description,
            "meta": TransactionHttpPresenter.present_meta(transaction),
        }

    @staticmethod
    def present_many(transactions: list[TransactionPlainDTO]) -> list[dict]:
        return [{
            "id": transaction.id,
            "type": transaction.type,
            "sender": TransactionParticipantHttpPresenter.present_preview(
                transaction.sender
            ) if transaction.sender else None,
            "receiver": TransactionParticipantHttpPresenter.present_preview(
                transaction.receiver
            ) if transaction.receiver else None,
            "description": transaction.description,
            "meta": TransactionHttpPresenter.present_meta(transaction),
        } for transaction in transactions]
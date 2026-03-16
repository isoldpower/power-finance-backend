from finances.domain.entities.transaction import Transaction, TransactionParticipant
from .update_mapper import UpdateMapper

from ..orm import TransactionModel


class TransactionMapper:
    TRANSACTION_EDITABLE_MAP: list[tuple[str, str]] = [
        ('send_wallet_id', 'sender.wallet_id'),
        ('send_amount', 'sender.amount'),
        ('receive_wallet_id', 'receiver.wallet_id'),
        ('receive_amount', 'receiver.amount'),
        ('description', 'description'),
        ('type', 'type'),
        ('category', 'category')
    ]

    @staticmethod
    def to_domain(model: TransactionModel) -> Transaction:
        return Transaction.from_persistence(
            id=model.id,
            sender=TransactionParticipant(
                wallet_id=model.send_wallet_id,
                amount=model.send_amount,
            ) if model.send_wallet else None,
            receiver=TransactionParticipant(
                wallet_id=model.receive_wallet_id,
                amount=model.receive_amount,
            ) if model.receive_wallet else None,
            description=model.description,
            created_at=model.created_at,
            type=model.type,
            category=model.category
        )

    @staticmethod
    def update_model(model: TransactionModel, entity: Transaction) -> TransactionModel:
        return UpdateMapper[TransactionModel, Transaction].update_model(
            model,
            entity,
            TransactionMapper.TRANSACTION_EDITABLE_MAP,
        )

    @staticmethod
    def get_changed_fields(model: TransactionModel, entity: Transaction) -> list[str]:
        return UpdateMapper[TransactionModel, Transaction].get_changed_fields(
            model,
            entity,
            TransactionMapper.TRANSACTION_EDITABLE_MAP,
            updated_list=["updated_at"]
        )

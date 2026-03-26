from finances.domain.entities import Transaction, TransactionParticipant
from finances.domain.value_objects import Money

from .update_mapper import UpdateMapper
from ..orm import TransactionModel


class TransactionMapper:
    TRANSACTION_EDITABLE_MAP: list[tuple[str, str]] = [
        ('send_wallet_id', 'sender.wallet_id'),
        ('send_amount', 'sender.money.amount'),
        ('receive_wallet_id', 'receiver.wallet_id'),
        ('receive_amount', 'receiver.money.amount'),
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
                money=Money(
                    amount=model.send_amount,
                    currency_code=model.send_wallet.currency.code,
                ),
            ) if model.send_wallet else None,
            receiver=TransactionParticipant(
                wallet_id=model.receive_wallet_id,
                money=Money(
                    amount=model.receive_amount,
                    currency_code=model.receive_wallet.currency.code,
                ),
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

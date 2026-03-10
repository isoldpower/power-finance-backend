from finances.domain.entities.transaction import Transaction, TransactionParticipant
from finances.infrastructure.orm.transaction import TransactionModel


class TransactionMapper:
    @staticmethod
    def to_domain(model: TransactionModel) -> Transaction:
        return Transaction(
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

from finances.domain.entities.transaction import Transaction, TransactionParticipant

from ..orm import TransactionModel


class TransactionMapper:
    TRANSACTION_EDITABLE_MAP = [
        ('send_wallet_id', 'sender.wallet_id'),
        ('send_amount', 'sender.amount'),
        ('receive_wallet_id', 'receiver.wallet_id'),
        ('receive_amount', 'receiver.amount'),
        ('description', 'description'),
        ('type', 'type'),
        ('category', 'category')
    ]

    @staticmethod
    def _resolve_attr(obj, path: str):
        current = obj
        for part in path.split("."):
            current = getattr(current, part)
            if not current:
                return None

        return current

    @staticmethod
    def _get_initial_key(path: str):
        return path.split(".")[0]

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

    @staticmethod
    def update_model(model: TransactionModel, entity: Transaction) -> TransactionModel:
        for model_field, entity_field in TransactionMapper.TRANSACTION_EDITABLE_MAP:
            entity_value = TransactionMapper._resolve_attr(entity, entity_field)
            model_value = getattr(model, model_field)

            if entity_value and model_value != entity_value:
                setattr(model, model_field, entity_value)

        return model

    @staticmethod
    def get_changed_fields(model: TransactionModel, entity: Transaction) -> list[str]:
        changed_fields = ["updated_at"]
        for model_field, entity_field in TransactionMapper.TRANSACTION_EDITABLE_MAP:
            entity_value = TransactionMapper._resolve_attr(entity, entity_field)
            model_value = getattr(model, model_field)

            if model_value != entity_value:
                changed_fields.append(model_field)

        return changed_fields

from uuid import UUID

from data_write_core.domain.entities import TransactionEntity
from data_write_core.domain.events import EventCollector
from data_write_core.domain.value_objects import TransactionMetadata, TransactionOrigin
from data_write_core.infrastructure.orm import TransactionModel


class TransactionMapper:
    @staticmethod
    def to_domain(model: TransactionModel) -> TransactionEntity:
        return TransactionEntity(
            id=model.id,
            user_id=str(model.user_id),
            wallet_id=model.wallet_id,
            metadata=TransactionMetadata(
                name=model.name,
                category=model.category,
                evidence_url=model.evidence_url,
                origin=TransactionOrigin(model.origin),
                chain_id=model.chain_id,
            ),
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            event_collector=EventCollector(),
        )

    @staticmethod
    def apply_to_model(model: TransactionModel, entity: TransactionEntity) -> TransactionModel:
        model.id = UUID(entity.unique_id)
        model.user_id = int(entity.user_id)
        model.wallet_id = entity.wallet_id
        model.chain_id = entity.chain_id
        model.name = entity.name
        model.category = entity.category
        model.evidence_url = entity.evidence_url
        model.origin = str(entity.origin)
        model.created_at = entity.created_at
        model.updated_at = entity.updated_at
        model.deleted_at = entity.deleted_at

        return model

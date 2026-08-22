from data_write_core.domain.entities import WalletEntity
from data_write_core.domain.events import EventCollector
from data_write_core.infrastructure.orm import WalletModel


class WalletMapper:
    @staticmethod
    def to_domain(model: WalletModel) -> WalletEntity:
        return WalletEntity(
            id=str(model.id),
            title=model.name,
            currency_code=model.currency_id,
            user_id=str(model.user_id),
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
            category=model.category,
            color=model.color,
            favorite=model.favorite,
            zero_balance=model.zero_balance,
            event_collector=EventCollector(),
        )

    @staticmethod
    def apply_to_model(model: WalletModel, entity: WalletEntity) -> WalletModel:
        model.id = entity.unique_id
        model.name = entity.title
        model.currency_id = entity.currency_code
        model.user_id = int(entity.user_id)
        model.created_at = entity.created_at
        model.deleted_at = entity.deleted_at
        model.category = entity.category
        model.color = entity.color
        model.favorite = entity.favorite
        model.zero_balance = entity.zero_balance

        return model

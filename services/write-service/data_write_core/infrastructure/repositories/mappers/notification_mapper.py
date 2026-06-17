from data_write_core.domain.entities import NotificationEntity
from data_write_core.domain.events import EventCollector
from data_write_core.infrastructure.orm import NotificationModel


class NotificationMapper:
    @staticmethod
    def to_domain(model: NotificationModel) -> NotificationEntity:
        return NotificationEntity(
            id=str(model.id),
            short=model.short,
            message=model.message,
            payload=model.payload,
            is_read=model.is_read,
            user_id=str(model.user_id),
            created_at=model.created_at,
            event_collector=EventCollector(),
        )

    @staticmethod
    def apply_to_model(model: NotificationModel, entity: NotificationEntity) -> NotificationModel:
        model.id = entity.unique_id
        model.short = entity.short
        model.message = entity.message
        model.payload = entity.payload
        model.is_read = entity.is_read
        model.user_id = int(entity.user_id)
        model.created_at = entity.created_at

        return model

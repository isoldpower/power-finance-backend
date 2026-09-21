from data_write_core.domain.entities import NotificationEntity
from data_write_core.domain.events import EventCollector
from data_write_core.infrastructure.orm import NotificationModel


class NotificationMapper:
    @staticmethod
    def to_domain(
        model: NotificationModel,
    ) -> NotificationEntity:
        return NotificationEntity(
            id=str(model.id),
            title=model.title,
            body=model.body,
            payload=model.payload,
            severity=model.severity,
            subject_type=model.subject_type or None,
            subject_id=model.subject_id or None,
            acknowledged_at=model.acknowledged_at,
            user_id=str(model.user_id),
            created_at=model.created_at,
            updated_at=model.updated_at,
            event_collector=EventCollector(),
        )

    @staticmethod
    def apply_to_model(
        model: NotificationModel,
        entity: NotificationEntity,
    ) -> NotificationModel:
        model.id = entity.unique_id
        model.title = entity.title
        model.body = entity.body
        model.payload = entity.payload
        model.severity = entity.severity
        model.subject_type = entity.subject_type or ""
        model.subject_id = entity.subject_id or ""
        model.acknowledged_at = entity.acknowledged_at
        model.user_id = int(entity.user_id)
        model.created_at = entity.created_at
        model.updated_at = entity.updated_at

        return model

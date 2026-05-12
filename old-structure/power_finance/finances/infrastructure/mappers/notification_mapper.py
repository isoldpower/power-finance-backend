from finances.domain.entities import Notification
from finances.infrastructure.orm import NotificationModel

from .update_mapper import UpdateMapper


class NotificationMapper:
    NOTIFICATION_EDITABLE_MAP: list[tuple[str, str]] = [
        ('user_id', 'user_id'),
        ('short', 'short'),
        ('message', 'message'),
        ('is_read', 'is_read'),
        ('payload', 'payload'),
    ]

    @staticmethod
    def to_domain(model: NotificationModel) -> Notification:
        return Notification(
            id=model.id,
            short=model.short,
            message=model.message,
            user_id=model.user_id,
            payload=model.payload,
            created_at=model.created_at,
            is_read=model.is_read,
        )

    @staticmethod
    def update_model(model: NotificationModel, entity: Notification) -> NotificationModel:
        return UpdateMapper[NotificationModel, Notification].update_model(
            model,
            entity,
            NotificationMapper.NOTIFICATION_EDITABLE_MAP,
        )

    @staticmethod
    def get_changed_fields(model: NotificationModel, entity: Notification) -> list[str]:
        return UpdateMapper[NotificationModel, Notification].get_changed_fields(
            model,
            entity,
            NotificationMapper.NOTIFICATION_EDITABLE_MAP,
        )
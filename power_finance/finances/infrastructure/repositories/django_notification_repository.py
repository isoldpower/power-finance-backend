from uuid import UUID

from finances.application.interfaces import NotificationRepository
from finances.domain.entities import Notification

from ..mappers import NotificationMapper
from ..orm import NotificationModel


class DjangoNotificationRepository(NotificationRepository):
    def get_notification_by_id(self, notification_id: UUID) -> Notification:
        requested_notification: NotificationModel = NotificationModel.objects.get(id=notification_id)

        return NotificationMapper.to_domain(requested_notification)

    def create_notification(self, entity: Notification) -> Notification:
        notification_model: NotificationModel = NotificationModel.objects.create(user_id=entity.user_id)

        NotificationMapper.update_model(notification_model, entity)
        notification_model.save()

        return NotificationMapper.to_domain(notification_model)
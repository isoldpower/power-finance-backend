from uuid import UUID

from django.utils import timezone

from finances.application.interfaces import NotificationRepository
from finances.domain.entities import Notification

from ..mappers import NotificationMapper
from ..orm import NotificationModel


class DjangoNotificationRepository(NotificationRepository):
    def get_notification_by_id(self, notification_id: UUID) -> Notification:
        requested_notification: NotificationModel = NotificationModel.objects.get(id=notification_id)

        return NotificationMapper.to_domain(requested_notification)

    def get_notifications_by_user_id(self, user_id: int) -> list[Notification]:
        requested_notifications = NotificationModel.objects.filter(user_id=user_id)
        return [NotificationMapper.to_domain(notification) for notification in requested_notifications]

    def mark_notifications_delivered(self, notification_ids: list[UUID] | str, user_id: int) -> list[Notification]:
        notifications = NotificationModel.objects.filter(
            user_id=user_id,
            received_at__isnull=True
        )
        if notification_ids != "all":
            notifications = notifications.filter(id__in=notification_ids)

        matching_ids = list(notifications.values_list('id', flat=True))
        notifications.update(received_at=timezone.now())

        updated_models = NotificationModel.objects.filter(id__in=matching_ids)
        return [NotificationMapper.to_domain(notification) for notification in updated_models]

    def create_notification(self, entity: Notification) -> Notification:
        notification_model: NotificationModel = NotificationModel.objects.create(user_id=entity.user_id)

        NotificationMapper.update_model(notification_model, entity)
        notification_model.save()

        return NotificationMapper.to_domain(notification_model)

    def mark_notification_delivered(self, notification_id: UUID) -> Notification:
        requested_notification: NotificationModel = NotificationModel.objects.get(id=notification_id)

        if not requested_notification.received_at:
            requested_notification.received_at = timezone.now()
            requested_notification.save(update_fields=['received_at'])

        return NotificationMapper.to_domain(requested_notification)
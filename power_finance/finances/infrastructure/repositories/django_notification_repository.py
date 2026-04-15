from uuid import UUID

from django.utils import timezone

from finances.application.interfaces import NotificationRepository
from finances.domain.entities import Notification

from ..mappers import NotificationMapper
from ..orm import NotificationModel


class DjangoNotificationRepository(NotificationRepository):
    async def get_notification_by_id(self, notification_id: UUID) -> Notification:
        requested_notification: NotificationModel = await NotificationModel.objects.aget(id=notification_id)

        return NotificationMapper.to_domain(requested_notification)

    async def get_notifications_by_user_id(self, user_id: int) -> list[Notification]:
        requested_notifications = NotificationModel.objects.filter(user_id=user_id)

        return [NotificationMapper.to_domain(notification) async for notification in requested_notifications]

    async def mark_notifications_delivered(self, notification_ids: list[UUID] | str, user_id: int) -> list[Notification]:
        notifications = NotificationModel.objects.filter(
            user_id=user_id,
            received_at__isnull=True
        )
        if notification_ids != "all":
            notifications = notifications.filter(id__in=notification_ids)

        now = timezone.now()
        notification_objects = [n async for n in notifications]
        await notifications.aupdate(received_at=now)
        for n in notification_objects:
            n.received_at = now

        return [NotificationMapper.to_domain(n) for n in notification_objects]

    async def create_notification(self, entity: Notification) -> Notification:
        notification_model = NotificationModel()
        NotificationMapper.update_model(notification_model, entity)
        await notification_model.asave()

        return NotificationMapper.to_domain(notification_model)

    async def mark_notification_delivered(self, notification_id: UUID) -> Notification:
        requested_notification: NotificationModel = await NotificationModel.objects.aget(id=notification_id)

        if not requested_notification.received_at:
            requested_notification.received_at = timezone.now()
            await requested_notification.asave(update_fields=['received_at'])

        return NotificationMapper.to_domain(requested_notification)
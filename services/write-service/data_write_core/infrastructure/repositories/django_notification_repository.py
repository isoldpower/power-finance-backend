from uuid import UUID

from data_write_core.application.interfaces import NotificationRepository
from data_write_core.domain.entities import NotificationEntity

from ..orm import NotificationModel
from .mappers import NotificationMapper


class DjangoNotificationRepository(NotificationRepository):
    async def create_notification(self, notification: NotificationEntity) -> NotificationEntity:
        created_notification = NotificationModel()
        NotificationMapper.apply_to_model(created_notification, notification)
        await created_notification.asave()

        refreshed = await NotificationModel.objects.aget(id=created_notification.id)
        return NotificationMapper.to_domain(refreshed)

    async def get_user_notification_by_id(
        self,
        notification_id: UUID,
        user_id: int,
    ) -> NotificationEntity:
        requested_notification: NotificationModel = await NotificationModel.objects.aget(
            id=notification_id,
            user_id=user_id,
        )

        return NotificationMapper.to_domain(requested_notification)

    async def get_user_notifications_by_ids(
        self,
        notification_ids: list[UUID],
        user_id: int,
    ) -> list[NotificationEntity]:
        queryset = NotificationModel.objects.filter(
            id__in=notification_ids,
            user_id=user_id,
        )

        return [NotificationMapper.to_domain(notification) async for notification in queryset]

    async def get_user_notifications(
        self,
        user_id: int,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[NotificationEntity]:
        queryset = NotificationModel.objects.filter(user_id=user_id).order_by("-created_at")

        start = offset or 0
        if limit is not None:
            queryset = queryset[start : start + limit]
        elif offset is not None:
            queryset = queryset[start:]

        return [NotificationMapper.to_domain(notification) async for notification in queryset]

    async def count_user_notifications(self, user_id: int) -> int:
        return await NotificationModel.objects.filter(user_id=user_id).acount()

    async def mark_notifications_read(
        self,
        notification_ids: list[UUID],
        user_id: int,
    ) -> None:
        await NotificationModel.objects.filter(
            id__in=notification_ids,
            user_id=user_id,
        ).aupdate(is_read=True)

    async def mark_notifications_unread(
        self,
        notification_ids: list[UUID],
        user_id: int,
    ) -> None:
        await NotificationModel.objects.filter(
            id__in=notification_ids,
            user_id=user_id,
        ).aupdate(is_read=False)

    async def hard_delete_notification(self, notification_id: UUID) -> None:
        await NotificationModel.objects.filter(id=notification_id).adelete()

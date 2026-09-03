from datetime import datetime
from uuid import UUID

from django.db.models import Count, Q
from write_service.common.pagination import PageRequest, apply_keyset

from data_write_core.application.interfaces import NotificationRepository
from data_write_core.domain.entities import NotificationEntity

from ..orm import NotificationModel
from .mappers import NotificationMapper


class DjangoNotificationRepository(NotificationRepository):
    async def create_notification(
        self,
        notification: NotificationEntity,
    ) -> NotificationEntity:
        created_notification = NotificationModel()
        NotificationMapper.apply_to_model(created_notification, notification)
        await created_notification.asave()

        refreshed_notifications = await NotificationModel.objects.aget(id=created_notification.id)
        return NotificationMapper.to_domain(refreshed_notifications)

    async def get_user_notification_by_id(
        self,
        notification_id: UUID,
        user_id: int,
    ) -> NotificationEntity:
        requested_notification: NotificationModel = await NotificationModel.objects.aget(
            id=notification_id, user_id=user_id
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
        page: PageRequest | None = None,
    ) -> list[NotificationEntity]:
        queryset = NotificationModel.objects.filter(user_id=user_id)
        notification_rows = (
            apply_keyset(queryset, page) if page else queryset.order_by("-created_at", "-id")
        )

        return [
            NotificationMapper.to_domain(notification) async for notification in notification_rows
        ]

    async def count_user_notifications(
        self,
        user_id: int,
    ) -> int:
        return await NotificationModel.objects.filter(user_id=user_id).acount()

    async def count_notification_badge(self, user_id: int) -> tuple[int, int]:
        """One aggregate rather than two counts: across two queries an
        acknowledgement landing between them could report a badge larger than
        the total it is a subset of."""

        counted = await NotificationModel.objects.filter(user_id=user_id).aaggregate(
            total=Count("id"),
            unacknowledged=Count("id", filter=Q(acknowledged_at__isnull=True)),
        )

        return (counted["unacknowledged"] or 0, counted["total"] or 0)

    async def acknowledge_notifications(
        self,
        notification_ids: list[UUID],
        user_id: int,
        acknowledged_at: datetime,
    ) -> None:
        await NotificationModel.objects.filter(
            id__in=notification_ids,
            user_id=user_id,
            acknowledged_at__isnull=True,
        ).aupdate(
            acknowledged_at=acknowledged_at,
            updated_at=acknowledged_at,
        )

    async def unacknowledge_notifications(
        self,
        notification_ids: list[UUID],
        user_id: int,
    ) -> None:
        await NotificationModel.objects.filter(
            id__in=notification_ids,
            user_id=user_id,
        ).aupdate(
            acknowledged_at=None,
            updated_at=None,
        )

    async def hard_delete_notification(
        self,
        notification_id: UUID,
    ) -> None:
        await NotificationModel.objects.filter(id=notification_id).adelete()

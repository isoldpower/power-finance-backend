import asyncio
from dataclasses import dataclass

from write_service.common.pagination import PageRequest

from ..bootstrap import get_repository_registry
from ..dtos import NotificationDTO, notification_to_dto
from ..interfaces import NotificationRepository


@dataclass(frozen=True)
class ListFallbackNotificationsQuery:
    user_id: int
    page: PageRequest


class ListFallbackNotificationsQueryHandler:
    def __init__(self, notification_repository: NotificationRepository | None = None) -> None:
        self._notification_repository = (
            notification_repository or get_repository_registry().notification_repository
        )

    async def handle(
        self, query: ListFallbackNotificationsQuery
    ) -> tuple[list[NotificationDTO], int]:
        notifications, total = await asyncio.gather(
            self._notification_repository.get_user_notifications(
                user_id=query.user_id,
                page=query.page,
            ),
            self._notification_repository.count_user_notifications(query.user_id),
        )

        return [notification_to_dto(notification) for notification in notifications], total

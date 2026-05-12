from dataclasses import dataclass

from finances.domain.entities import Notification

from ...bootstrap import get_repository_registry
from ...interfaces import NotificationRepository


@dataclass(frozen=True)
class ListNotificationsQuery:
    user_id: int


class ListNotificationsQueryHandler:
    def __init__(
            self,
            notification_repository: NotificationRepository | None = None,
    ) -> None:
        registry = get_repository_registry()
        self._notification_repository = notification_repository or registry.notification_repository

    async def handle(self, query: ListNotificationsQuery) -> list[Notification]:
        return await self._notification_repository.get_notifications_by_user_id(query.user_id)

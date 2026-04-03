from dataclasses import dataclass

from finances.application.interfaces import NotificationRepository
from finances.domain.entities import Notification
from finances.infrastructure.repositories import DjangoNotificationRepository


@dataclass(frozen=True)
class ListNotificationsQuery:
    user_id: int


class ListNotificationsQueryHandler:
    def __init__(
            self,
            notification_repository: NotificationRepository | None = None,
    ) -> None:
        self._notification_repository = notification_repository or DjangoNotificationRepository()

    def handle(self, query: ListNotificationsQuery) -> list[Notification]:
        return self._notification_repository.get_notifications_by_user_id(query.user_id)

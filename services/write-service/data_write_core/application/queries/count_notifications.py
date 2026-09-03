from dataclasses import dataclass

from ..bootstrap import get_repository_registry
from ..interfaces import NotificationRepository


@dataclass(frozen=True)
class CountFallbackNotificationsQuery:
    user_id: int


@dataclass(frozen=True)
class FallbackNotificationCounts:
    unacknowledged: int
    total: int


class CountFallbackNotificationsQueryHandler:
    def __init__(self, notification_repository: NotificationRepository | None = None) -> None:
        self._notification_repository = (
            notification_repository or get_repository_registry().notification_repository
        )

    async def handle(self, query: CountFallbackNotificationsQuery) -> FallbackNotificationCounts:
        unacknowledged, total = await self._notification_repository.count_notification_badge(
            query.user_id
        )

        return FallbackNotificationCounts(
            unacknowledged=unacknowledged,
            total=total,
        )

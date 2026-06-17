from dataclasses import dataclass
from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist

from data_write_core.domain.exceptions import NotificationNotFoundError

from ..bootstrap import get_repository_registry
from ..dtos import NotificationDTO, notification_to_dto
from ..interfaces import NotificationRepository


@dataclass(frozen=True)
class GetFallbackNotificationQuery:
    user_id: int
    notification_id: UUID


class GetFallbackNotificationQueryHandler:
    def __init__(self, notification_repository: NotificationRepository | None = None) -> None:
        self._notification_repository = (
            notification_repository or get_repository_registry().notification_repository
        )

    async def handle(self, query: GetFallbackNotificationQuery) -> NotificationDTO:
        try:
            notification = await self._notification_repository.get_user_notification_by_id(
                notification_id=query.notification_id,
                user_id=query.user_id,
            )
        except ObjectDoesNotExist as exc:
            raise NotificationNotFoundError(query.notification_id) from exc

        return notification_to_dto(notification)

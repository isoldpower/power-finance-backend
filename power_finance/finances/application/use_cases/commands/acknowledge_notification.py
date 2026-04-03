from dataclasses import dataclass
from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist

from finances.application.interfaces import NotificationRepository
from finances.domain.entities import Notification
from finances.infrastructure.repositories import DjangoNotificationRepository


@dataclass(frozen=True)
class AcknowledgeNotificationCommand:
    user_id: int
    notification_id: UUID


class AcknowledgeNotificationCommandHandler:
    def __init__(
            self,
            notification_repository: NotificationRepository | None = None,
    ) -> None:
        self._notification_repository = notification_repository or DjangoNotificationRepository()

    def handle(self, command: AcknowledgeNotificationCommand) -> Notification:
        try:
            notification = self._notification_repository.get_notification_by_id(command.notification_id)
        except ObjectDoesNotExist:
            raise ValueError(f"Notification with id {command.notification_id} not found")

        if notification.user_id != command.user_id:
            raise PermissionError("User is not authorized to acknowledge this notification")

        return self._notification_repository.mark_notification_delivered(command.notification_id)


@dataclass(frozen=True)
class BatchAcknowledgeNotificationCommand:
    user_id: int
    notification_ids: list[UUID] | str


class BatchAcknowledgeNotificationCommandHandler:
    def __init__(
            self,
            notification_repository: NotificationRepository | None = None,
    ) -> None:
        self._notification_repository = notification_repository or DjangoNotificationRepository()

    def handle(self, command: BatchAcknowledgeNotificationCommand) -> list[str]:
        read_notifications = self._notification_repository.mark_notifications_delivered(
            command.notification_ids,
            command.user_id,
        )
        print('1', read_notifications)

        return [str(notification.id) for notification in read_notifications]

from abc import ABC, abstractmethod
from uuid import UUID

from finances.domain.entities import Notification


class NotificationRepository(ABC):
    @abstractmethod
    async def get_notification_by_id(self, notification_id: UUID) -> Notification:
        raise NotImplementedError()

    @abstractmethod
    async def get_notifications_by_user_id(self, user_id: int) -> list[Notification]:
        raise NotImplementedError()

    @abstractmethod
    async def create_notification(self, entity: Notification) -> Notification:
        raise NotImplementedError()

    @abstractmethod
    async def mark_notification_delivered(self, notification_id: UUID) -> Notification:
        raise NotImplementedError()

    @abstractmethod
    async def mark_notifications_delivered(self, notification_ids: list[UUID] | str, user_id: int) -> list[Notification]:
        raise NotImplementedError()




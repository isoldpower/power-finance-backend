from abc import ABC, abstractmethod
from uuid import UUID

from data_write_core.domain.entities import NotificationEntity


class NotificationRepository(ABC):
    @abstractmethod
    async def create_notification(self, notification: NotificationEntity) -> NotificationEntity:
        raise NotImplementedError()

    @abstractmethod
    async def get_user_notification_by_id(
        self,
        notification_id: UUID,
        user_id: int,
    ) -> NotificationEntity:
        raise NotImplementedError()

    @abstractmethod
    async def get_user_notifications_by_ids(
        self,
        notification_ids: list[UUID],
        user_id: int,
    ) -> list[NotificationEntity]:
        raise NotImplementedError()

    @abstractmethod
    async def get_user_notifications(
        self,
        user_id: int,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[NotificationEntity]:
        raise NotImplementedError()

    @abstractmethod
    async def count_user_notifications(self, user_id: int) -> int:
        raise NotImplementedError()

    @abstractmethod
    async def mark_notifications_read(
        self,
        notification_ids: list[UUID],
        user_id: int,
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def mark_notifications_unread(
        self,
        notification_ids: list[UUID],
        user_id: int,
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def hard_delete_notification(self, notification_id: UUID) -> None:
        raise NotImplementedError()

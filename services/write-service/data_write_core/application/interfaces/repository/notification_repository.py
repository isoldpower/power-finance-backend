from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from write_service.common.pagination import PageRequest

from data_write_core.domain.entities import NotificationEntity


class NotificationRepository(ABC):
    @abstractmethod
    async def create_notification(
        self,
        notification: NotificationEntity,
    ) -> NotificationEntity:
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
        page: PageRequest | None = None,
    ) -> list[NotificationEntity]:
        raise NotImplementedError()

    @abstractmethod
    async def count_user_notifications(
        self,
        user_id: int,
    ) -> int:
        raise NotImplementedError()

    @abstractmethod
    async def acknowledge_notifications(
        self,
        notification_ids: list[UUID],
        user_id: int,
        acknowledged_at: datetime,
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def unacknowledge_notifications(
        self,
        notification_ids: list[UUID],
        user_id: int,
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def hard_delete_notification(
        self,
        notification_id: UUID,
    ) -> None:
        raise NotImplementedError()

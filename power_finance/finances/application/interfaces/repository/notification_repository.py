from abc import ABC, abstractmethod
from uuid import UUID

from finances.domain.entities import Notification


class NotificationRepository(ABC):
    @abstractmethod
    def get_notification_by_id(self, notification_id: UUID) -> Notification:
        raise NotImplementedError()

    @abstractmethod
    def create_notification(self, entity: Notification) -> Notification:
        raise NotImplementedError()

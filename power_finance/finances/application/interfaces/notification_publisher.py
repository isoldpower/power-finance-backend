from abc import ABC, abstractmethod

from finances.domain.entities import Notification


class NotificationChannel(ABC):
    @abstractmethod
    async def get(self, timeout: float | None = None) -> dict:
        raise NotImplementedError()


class NotificationBroker(ABC):
    @abstractmethod
    async def subscribe(self, user_id: int) -> NotificationChannel:
        raise NotImplementedError()

    @abstractmethod
    async def unsubscribe(self, user_id: int, queue: NotificationChannel) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def publish(self, user_id: int, payload: dict) -> None:
        raise NotImplementedError()

class NotificationPublisher(ABC):
    @abstractmethod
    async def publish_notification(self, notification: Notification) -> None:
        raise NotImplementedError()

from abc import ABC, abstractmethod

from finances.domain.entities import Notification


class NotificationChannel(ABC):
    @abstractmethod
    def get(
            self,
            block: bool,
            timeout: float
    ) -> dict:
        raise NotImplementedError()


class NotificationBroker(ABC):
    @abstractmethod
    def subscribe(self, user_id: int) -> NotificationChannel:
        raise NotImplementedError()

    @abstractmethod
    def unsubscribe(self, user_id: int, queue: NotificationChannel) -> None:
        raise NotImplementedError()

    @abstractmethod
    def publish(self, user_id: int, payload: dict) -> None:
        raise NotImplementedError()

class NotificationPublisher(ABC):
    @abstractmethod
    def publish_notification(self, notification: Notification) -> None:
        raise NotImplementedError()

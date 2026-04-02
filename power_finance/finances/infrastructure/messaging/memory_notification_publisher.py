from finances.application.interfaces import NotificationPublisher, NotificationBroker
from finances.domain.entities import Notification


class InMemorySseNotificationPublisher(NotificationPublisher):
    _message_broker: NotificationBroker

    def __init__(self, broker: NotificationBroker) -> None:
        self._broker = broker

    def publish_notification(self, notification: Notification) -> None:
        self._broker.publish(
            user_id=notification.user_id,
            payload={
                "id": str(notification.id),
                "short": notification.short,
                "message": notification.message,
                "created_at": notification.created_at.isoformat(),
                "payload": notification.payload,
            },
        )
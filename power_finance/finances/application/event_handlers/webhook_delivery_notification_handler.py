from finances.domain.events import WebhookDeliveryStatusChangedEvent
from finances.domain.entities import Notification

from ..interfaces import (
    WebhookDeliveryRepository,
    NotificationRepository,
    WebhookRepository,
    EventPayloadFactory,
    NotificationPublisher,
)


class WebhookDeliveryNotificationHandler:
    _delivery_repository: WebhookDeliveryRepository
    _notification_repository: NotificationRepository
    _webhook_repository: WebhookRepository
    _payload_factory: EventPayloadFactory
    _notification_publisher: NotificationPublisher

    def __init__(
            self,
            notification_repository: NotificationRepository,
            delivery_repository: WebhookDeliveryRepository,
            webhook_repository: WebhookRepository,
            payload_factory: EventPayloadFactory,
            notification_publisher: NotificationPublisher,
    ):
        self._delivery_repository = delivery_repository
        self._notification_repository = notification_repository
        self._webhook_repository = webhook_repository
        self._payload_factory = payload_factory
        self._notification_publisher = notification_publisher

    def __call__(self, event: WebhookDeliveryStatusChangedEvent) -> None:
        payload = self._payload_factory.from_delivery_status_changed(event)
        notification_data = Notification.create(
            short="Webhook delivery status updated",
            message=f'Webhook (ID {event.endpoint_id}) delivery status was set to "{event.status}". '
                    f'You can find more information in developer documentation.',
            user_id=event.user_id,
            payload=payload
        )
        notification = self._notification_repository.create_notification(notification_data)

        self._notification_publisher.publish_notification(notification)

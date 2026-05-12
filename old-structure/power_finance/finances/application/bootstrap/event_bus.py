from finances.domain.events import (
    TransactionCreatedEvent,
    TransactionDeletedEvent,
    WebhookDeliveryStatusChangedEvent,
)
from finances.infrastructure.integrations import WebhookDispatcher
from finances.infrastructure.messaging import InMemoryEventBus

from ..event_handlers import (
    TransactionCreatedWebhookHandler,
    TransactionDeletedWebhookHandler,
    WebhookDeliveryNotificationHandler,
)
from ..interfaces import (
    WebhookDeliveryRepository,
    WalletRepository,
    WebhookRepository,
    EventPayloadFactory,
    EventBus,
    NotificationPublisher,
    NotificationRepository,
    WebhookPayloadRepository,
)


def initialize_event_bus(
        webhook_repository: WebhookRepository,
        delivery_repository: WebhookDeliveryRepository,
        wallet_repository: WalletRepository,
        payload_repository: WebhookPayloadRepository,
        payload_factory: EventPayloadFactory,
        dispatcher: WebhookDispatcher,
        notification_publisher: NotificationPublisher,
        notification_repository: NotificationRepository,
) -> EventBus:
    event_bus = InMemoryEventBus()
    event_bus.subscribe(TransactionCreatedEvent, TransactionCreatedWebhookHandler(
        webhook_repository=webhook_repository,
        delivery_repository=delivery_repository,
        wallet_repository=wallet_repository,
        payload_factory=payload_factory,
        payload_repository=payload_repository,
        dispatcher=dispatcher,
        event_bus=event_bus,
    ))
    event_bus.subscribe(TransactionDeletedEvent, TransactionDeletedWebhookHandler(
        webhook_repository=webhook_repository,
        delivery_repository=delivery_repository,
        wallet_repository=wallet_repository,
        payload_repository=payload_repository,
        payload_factory=payload_factory,
        dispatcher=dispatcher,
        event_bus=event_bus,
    ))
    event_bus.subscribe(WebhookDeliveryStatusChangedEvent, WebhookDeliveryNotificationHandler(
        notification_repository=notification_repository,
        delivery_repository=delivery_repository,
        webhook_repository=webhook_repository,
        payload_factory=payload_factory,
        notification_publisher=notification_publisher,
    ))

    return event_bus
from dataclasses import dataclass

from finances.domain.events import (
    TransactionCreatedEvent,
    TransactionUpdatedEvent,
    TransactionDeletedEvent,
    WebhookDeliveryStatusChangedEvent,
)
from finances.infrastructure.integrations import WebhookDispatcher
from finances.infrastructure.messaging import InMemoryEventBus

from .event_handlers import (
    TransactionCreatedWebhookHandler,
    TransactionUpdatedWebhookHandler,
    TransactionDeletedWebhookHandler,
    WebhookDeliveryNotificationHandler,
)
from .interfaces import (
    WebhookDeliveryRepository,
    WalletRepository,
    WebhookRepository,
    EventPayloadFactory,
    EventBus,
    NotificationPublisher,
    NotificationRepository,
    NotificationBroker,
)


@dataclass(frozen=True)
class ApplicationState:
    initialized: bool = False
    event_bus: EventBus | None = None
    broker: NotificationBroker | None = None


application: ApplicationState | None = None

def bootstrap_application(
        webhook_repository: WebhookRepository,
        delivery_repository: WebhookDeliveryRepository,
        wallet_repository: WalletRepository,
        payload_factory: EventPayloadFactory,
        dispatcher: WebhookDispatcher,
        notification_broker: NotificationBroker,
        notification_publisher: NotificationPublisher,
        notification_repository: NotificationRepository,
):
    global application

    if application:
        return

    application = ApplicationState(
        initialized=True,
        broker=notification_broker,
        event_bus = initialize_event_bus(
            webhook_repository=webhook_repository,
            delivery_repository=delivery_repository,
            wallet_repository=wallet_repository,
            payload_factory=payload_factory,
            dispatcher=dispatcher,
            notification_publisher=notification_publisher,
            notification_repository=notification_repository,
        )
    )

def initialize_event_bus(
        webhook_repository: WebhookRepository,
        delivery_repository: WebhookDeliveryRepository,
        wallet_repository: WalletRepository,
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
        dispatcher=dispatcher,
        event_bus=event_bus,
    ))
    event_bus.subscribe(TransactionUpdatedEvent, TransactionUpdatedWebhookHandler(
        webhook_repository=webhook_repository,
        delivery_repository=delivery_repository,
        wallet_repository=wallet_repository,
        payload_factory=payload_factory,
        dispatcher=dispatcher,
        event_bus=event_bus,
    ))
    event_bus.subscribe(TransactionDeletedEvent, TransactionDeletedWebhookHandler(
        webhook_repository=webhook_repository,
        delivery_repository=delivery_repository,
        wallet_repository=wallet_repository,
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

def get_event_bus() -> EventBus:
    if application is None or not application.initialized:
        raise RuntimeError("Application is not bootstrapped or still initializing")
    return application.event_bus
from dataclasses import dataclass

from finances.domain.events import TransactionCreatedEvent
from finances.infrastructure.integrations import WebhookDispatcher
from finances.infrastructure.messaging import InMemoryEventBus

from .event_handlers import TransactionCreatedWebhookHandler
from .interfaces import (
    WebhookDeliveryRepository,
    EventPayloadFactory,
    EventBus, WalletRepository,
)

from .interfaces import (
    WebhookRepository,
)


@dataclass(frozen=True)
class ApplicationState:
    initialized: bool = False
    event_bus: EventBus | None = None


application: ApplicationState | None = None

def bootstrap_application(
        webhook_repository: WebhookRepository,
        delivery_repository: WebhookDeliveryRepository,
        wallet_repository: WalletRepository,
        payload_factory: EventPayloadFactory,
        dispatcher: WebhookDispatcher,
):
    global application

    if application:
        return

    application = ApplicationState(
        initialized=True,
        event_bus = initialize_event_bus(
            webhook_repository=webhook_repository,
            delivery_repository=delivery_repository,
            wallet_repository=wallet_repository,
            payload_factory=payload_factory,
            dispatcher=dispatcher,
        )
    )

def initialize_event_bus(
        webhook_repository: WebhookRepository,
        delivery_repository: WebhookDeliveryRepository,
        wallet_repository: WalletRepository,
        payload_factory: EventPayloadFactory,
        dispatcher: WebhookDispatcher,
) -> EventBus:
    event_bus = InMemoryEventBus()
    event_bus.subscribe(TransactionCreatedEvent, TransactionCreatedWebhookHandler(
        webhook_repository=webhook_repository,
        delivery_repository=delivery_repository,
        wallet_repository=wallet_repository,
        payload_factory=payload_factory,
        dispatcher=dispatcher,
    ))

    return event_bus

def get_event_bus() -> EventBus:
    if application is None or not application.initialized:
        raise RuntimeError("Application is not bootstrapped or still initializing")
    return application.event_bus
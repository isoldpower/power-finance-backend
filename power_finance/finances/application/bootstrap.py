from dataclasses import dataclass

from celery import Celery
from redis import Redis

from finances.domain.events import (
    TransactionCreatedEvent,
    TransactionUpdatedEvent,
    TransactionDeletedEvent,
    WebhookDeliveryStatusChangedEvent,
)
from finances.infrastructure.integrations import WebhookDispatcher
from finances.infrastructure.messaging import InMemoryEventBus
from finances.infrastructure.repositories import (
    DjangoWebhookDeliveryRepository,
    DjangoWebhookRepository,
    DjangoWalletRepository,
    DjangoNotificationRepository,
    DjangoTransactionRepository,
    DjangoCurrencyRepository, DjangoWebhookPayloadRepository,
)
from finances.infrastructure.selectors import (
    DjangoWalletSelectorsCollection,
    DjangoTransactionSelectorsCollection,
)

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
    CurrencyRepository,
    TransactionRepository,
    WalletSelectorsCollection,
    TransactionSelectorsCollection,
    WebhookPayloadRepository,
)


@dataclass(frozen=True)
class RepositoryRegistry:
    delivery_repository: WebhookDeliveryRepository
    webhook_repository: WebhookRepository
    wallet_repository: WalletRepository
    currency_repository: CurrencyRepository
    notification_repository: NotificationRepository
    transaction_repository: TransactionRepository
    wallet_selectors: WalletSelectorsCollection
    transaction_selectors: TransactionSelectorsCollection
    payload_repository: WebhookPayloadRepository


@dataclass(frozen=True)
class ApplicationState:
    event_bus: EventBus
    broker: NotificationBroker
    redis: Redis
    celery: Celery
    repository_registry: RepositoryRegistry
    initialized: bool = False


application: ApplicationState | None = None

def bootstrap_application(
        payload_factory: EventPayloadFactory,
        dispatcher: WebhookDispatcher,
        redis: Redis,
        celery: Celery,
        notification_broker: NotificationBroker,
        notification_publisher: NotificationPublisher,
):
    global application

    if application:
        return

    repository_registry = initialize_repositories()
    application = ApplicationState(
        initialized=True,
        redis=redis,
        broker=notification_broker,
        celery=celery,
        repository_registry=repository_registry,
        event_bus = initialize_event_bus(
            webhook_repository=repository_registry.webhook_repository,
            delivery_repository=repository_registry.delivery_repository,
            wallet_repository=repository_registry.wallet_repository,
            payload_repository=repository_registry.payload_repository,
            payload_factory=payload_factory,
            dispatcher=dispatcher,
            notification_publisher=notification_publisher,
            notification_repository=repository_registry.notification_repository,
        )
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
    event_bus.subscribe(TransactionUpdatedEvent, TransactionUpdatedWebhookHandler(
        webhook_repository=webhook_repository,
        delivery_repository=delivery_repository,
        wallet_repository=wallet_repository,
        payload_repository=payload_repository,
        payload_factory=payload_factory,
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

def initialize_repositories() -> RepositoryRegistry:
    return RepositoryRegistry(
        delivery_repository=DjangoWebhookDeliveryRepository(),
        webhook_repository=DjangoWebhookRepository(),
        wallet_repository=DjangoWalletRepository(),
        notification_repository=DjangoNotificationRepository(),
        transaction_repository=DjangoTransactionRepository(),
        currency_repository=DjangoCurrencyRepository(),
        payload_repository=DjangoWebhookPayloadRepository(),
        wallet_selectors=DjangoWalletSelectorsCollection(),
        transaction_selectors=DjangoTransactionSelectorsCollection(),
    )


def get_event_bus() -> EventBus:
    if application is None or not application.initialized:
        raise RuntimeError("Application is not bootstrapped or still initializing")
    return application.event_bus

def get_repository_registry() -> RepositoryRegistry:
    if application is None or not application.initialized:
        raise RuntimeError("Application is not bootstrapped or still initializing")
    return application.repository_registry

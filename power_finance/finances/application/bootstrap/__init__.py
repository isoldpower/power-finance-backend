from redis.asyncio.client import Redis

from finances.infrastructure.integrations import (
    WebhookDispatcher,
    WebhookPayloadFactory,
    HttpSender,
)
from finances.infrastructure.messaging import (
    RedisNotificationBroker,
    InMemorySseNotificationPublisher,
)

from ..interfaces import EventBus
from .celery import initialize_celery
from .redis import initialize_redis
from .event_bus import initialize_event_bus
from .repositories import initialize_repositories
from .state import (
    ApplicationEnvironment,
    ApplicationState,
    RepositoryRegistry,
)


application: ApplicationState | None = None

def bootstrap_application(environment: ApplicationEnvironment):
    global application

    if application:
        return

    repository_registry = initialize_repositories()
    redis_clients = initialize_redis(environment)
    celery_client = initialize_celery(environment)
    notification_broker = RedisNotificationBroker(redis_client=redis_clients.async_client)

    application = ApplicationState(
        initialized=True,
        redis=redis_clients.async_client,
        sync_redis=redis_clients.sync_client,
        broker=notification_broker,
        celery=celery_client,
        repository_registry=repository_registry,
        event_bus=initialize_event_bus(
            webhook_repository=repository_registry.webhook_repository,
            delivery_repository=repository_registry.delivery_repository,
            wallet_repository=repository_registry.wallet_repository,
            payload_repository=repository_registry.payload_repository,
            payload_factory=WebhookPayloadFactory(),
            dispatcher=WebhookDispatcher(HttpSender()),
            notification_publisher=InMemorySseNotificationPublisher(broker=notification_broker),
            notification_repository=repository_registry.notification_repository,
        )
    )


def get_event_bus() -> EventBus:
    if application is None or not application.initialized:
        raise RuntimeError("Application is not bootstrapped or still initializing")
    return application.event_bus

def get_repository_registry() -> RepositoryRegistry:
    if application is None or not application.initialized:
        raise RuntimeError("Application is not bootstrapped or still initializing")
    return application.repository_registry

def get_redis_client(sync: bool = True) -> Redis:
    if application is None or not application.initialized:
        raise RuntimeError("Application is not bootstrapped or still initializing")

    return application.sync_redis if sync else application.redis

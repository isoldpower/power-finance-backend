from dataclasses import dataclass

from celery import Celery
from redis.asyncio.client import Redis
from redis import Redis as SyncRedis

from ..interfaces import (
    WebhookDeliveryRepository,
    WalletRepository,
    WebhookRepository,
    EventBus,
    NotificationRepository,
    NotificationBroker,
    CurrencyRepository,
    TransactionRepository,
    WalletSelectorsCollection,
    TransactionSelectorsCollection,
    WebhookPayloadRepository,
)


@dataclass(frozen=True)
class ApplicationEnvironment:
    app_name: str
    redis_host: str
    redis_port: int
    redis_password: str
    redis_default_db_index: int
    redis_celery_db_index: int
    rabbitmq_host: str
    rabbitmq_port: int
    rabbitmq_user: str
    rabbitmq_password: str
    celery_beat_filename: str


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
class RedisClient:
    sync_client: SyncRedis
    async_client: Redis


@dataclass(frozen=True)
class ApplicationState:
    event_bus: EventBus
    broker: NotificationBroker
    redis: Redis
    sync_redis: SyncRedis
    celery: Celery
    repository_registry: RepositoryRegistry
    initialized: bool = False
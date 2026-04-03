from django.apps import AppConfig
from django.conf import settings


class FinancesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'finances'

    def ready(self) -> None:
        from finances.application.bootstrap import bootstrap_application
        from finances.infrastructure.integrations import (
            HttpSender,
            WebhookDispatcher,
            WebhookPayloadFactory,
        )
        from finances.infrastructure.repositories import (
            DjangoWebhookRepository,
            DjangoWebhookDeliveryRepository,
            DjangoWalletRepository,
        )
        from finances.infrastructure.messaging import (
            InMemorySseNotificationPublisher,
            RedisNotificationBroker,
        )
        from finances.infrastructure.repositories import DjangoNotificationRepository
        from finances.infrastructure.redis import build_redis_client

        http_sender = HttpSender()
        redis_client = build_redis_client(settings.RESOLVED_ENV.get('REDIS_URL'))
        notification_broker = RedisNotificationBroker(redis_client=redis_client)
        bootstrap_application(
            delivery_repository=DjangoWebhookDeliveryRepository(),
            webhook_repository=DjangoWebhookRepository(),
            wallet_repository=DjangoWalletRepository(),
            payload_factory=WebhookPayloadFactory(),
            dispatcher=WebhookDispatcher(sender=http_sender),
            notification_repository=DjangoNotificationRepository(),
            notification_publisher=InMemorySseNotificationPublisher(broker=notification_broker),
            redis=redis_client,
            notification_broker=notification_broker,
        )

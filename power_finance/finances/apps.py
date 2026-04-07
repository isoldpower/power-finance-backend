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
        from finances.infrastructure.messaging import (
            InMemorySseNotificationPublisher,
            RedisNotificationBroker,
        )
        from finances.infrastructure.redis import build_redis_client
        from finances.infrastructure.celery import build_celery_client

        webhook_dispatcher = WebhookDispatcher(HttpSender())
        webhook_factory = WebhookPayloadFactory()
        redis_client = build_redis_client(settings.RESOLVED_ENV.get('REDIS_URL'))
        celery_client = build_celery_client(settings.RESOLVED_ENV)
        notification_broker = RedisNotificationBroker(redis_client=redis_client)
        notification_publisher = InMemorySseNotificationPublisher(broker=notification_broker)
        bootstrap_application(
            payload_factory=webhook_factory,
            dispatcher=webhook_dispatcher,
            notification_publisher=notification_publisher,
            notification_broker=notification_broker,
            redis=redis_client,
            celery=celery_client,
        )

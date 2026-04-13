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
        redis_client = build_redis_client(
            host=settings.RESOLVED_ENV['REDIS_HOST'],
            port=settings.RESOLVED_ENV['REDIS_PORT'],
            password=settings.RESOLVED_ENV['REDIS_PASSWORD'],
        )
        celery_client = build_celery_client(
            app_name=settings.RESOLVED_ENV['APP_NAME'],
            rmq_host=settings.RESOLVED_ENV['RABBIT_MQ_HOST'],
            rmq_port=settings.RESOLVED_ENV['RABBIT_MQ_PORT'],
            rmq_user=settings.RESOLVED_ENV['RABBIT_MQ_USER'],
            rmq_password=settings.RESOLVED_ENV['RABBIT_MQ_PASSWORD'],
            redis_host=settings.RESOLVED_ENV['REDIS_HOST'],
            redis_port=settings.RESOLVED_ENV['REDIS_PORT'],
            redis_password=settings.RESOLVED_ENV['REDIS_PASSWORD'],
            redis_celery_db=settings.RESOLVED_ENV['REDIS_CELERY_DATABASE_INDEX'],
            beat_schedule_filename=settings.RESOLVED_ENV['CELERY_BEAT_SCHEDULE_FILENAME'],
        )
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

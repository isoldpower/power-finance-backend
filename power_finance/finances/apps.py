from django.apps import AppConfig


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
            InMemoryNotificationBroker
        )
        from finances.infrastructure.repositories import DjangoNotificationRepository

        http_sender = HttpSender()
        notification_broker = InMemoryNotificationBroker()
        bootstrap_application(
            delivery_repository=DjangoWebhookDeliveryRepository(),
            webhook_repository=DjangoWebhookRepository(),
            wallet_repository=DjangoWalletRepository(),
            payload_factory=WebhookPayloadFactory(),
            dispatcher=WebhookDispatcher(sender=http_sender),
            notification_repository=DjangoNotificationRepository(),
            notification_publisher=InMemorySseNotificationPublisher(broker=notification_broker),
            notification_broker=notification_broker,
        )

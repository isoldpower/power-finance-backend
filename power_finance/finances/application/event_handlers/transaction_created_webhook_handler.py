from django.db import transaction

from finances.domain.entities import WebhookType, Webhook
from finances.domain.events import TransactionCreatedEvent, EventCollector
from finances.infrastructure.integrations import WebhookDispatcher

from .event_webhook_handler import EventWebhookHandler
from ..interfaces import (
    WebhookRepository,
    WalletRepository,
    WebhookDeliveryRepository,
    EventPayloadFactory,
    EventBus,
)


class TransactionCreatedWebhookHandler(EventWebhookHandler):
    _webhook_repository: WebhookRepository
    _delivery_repository: WebhookDeliveryRepository
    _payload_factory: EventPayloadFactory

    def __init__(
            self,
            webhook_repository: WebhookRepository,
            delivery_repository: WebhookDeliveryRepository,
            wallet_repository: WalletRepository,
            payload_factory: EventPayloadFactory,
            dispatcher: WebhookDispatcher,
            event_bus: EventBus,
    ):
        super().__init__(
            event_type=WebhookType.TransactionCreate,
            delivery_repository=delivery_repository,
            dispatcher=dispatcher,
            event_bus=event_bus,
        )

        self._webhook_repository = webhook_repository
        self._wallet_repository = wallet_repository
        self._payload_factory = payload_factory

    @transaction.atomic
    def _handle_single_endpoint(
            self,
            webhook: Webhook,
            event: TransactionCreatedEvent
    ):
        request_body = self._payload_factory.from_transaction_created(event)
        delivery = self.handle_dispatch_webhook_delivery(
            webhook=webhook,
            event_id=event.event_id
        )

        self.handle_webhook_delivery_attempt(
            webhook=webhook,
            delivery_id=delivery.id,
            request_body=request_body,
        )

    def __call__(self, event: TransactionCreatedEvent) -> None:
        transaction_wallet = self._wallet_repository.get_wallet_by_id(
            event.sender.wallet_id if event.sender else event.receiver.wallet_id
        )
        webhooks = self._webhook_repository.get_webhooks_by_type(
            user_id=transaction_wallet.user_id,
            event_type=WebhookType.TransactionCreate
        )

        for webhook in webhooks:
            self._handle_single_endpoint(
                webhook=webhook,
                event=event
            )
from finances.domain.entities import WebhookType, Webhook
from finances.domain.events import TransactionUpdatedEvent
from finances.infrastructure.integrations import WebhookDispatcher

from .event_webhook_handler import EventWebhookHandler
from ..interfaces import (
    WebhookRepository,
    WalletRepository,
    WebhookDeliveryRepository,
    EventPayloadFactory,
)


class TransactionUpdatedWebhookHandler(EventWebhookHandler):
    _webhook_repository: WebhookRepository
    _wallet_repository: WalletRepository
    _payload_factory: EventPayloadFactory

    def __init__(
            self,
            webhook_repository: WebhookRepository,
            delivery_repository: WebhookDeliveryRepository,
            wallet_repository: WalletRepository,
            payload_factory: EventPayloadFactory,
            dispatcher: WebhookDispatcher
    ):
        super().__init__(
            event_type=WebhookType.TransactionUpdate,
            delivery_repository=delivery_repository,
            dispatcher=dispatcher,
        )

        self._payload_factory = payload_factory
        self._webhook_repository = webhook_repository
        self._wallet_repository = wallet_repository

    def _handle_single_endpoint(
            self,
            webhook: Webhook,
            event: TransactionUpdatedEvent
    ):
        request_body = self._payload_factory.from_transaction_updated(event)
        delivery = self.handle_dispatch_webhook_delivery(
            webhook=webhook,
            event_id=event.event_id
        )

        self.handle_webhook_delivery_attempt(
            webhook,
            delivery_id=delivery.id,
            request_body=request_body,
        )

    def __call__(self, event: TransactionUpdatedEvent) -> None:
        transaction_wallet = self._wallet_repository.get_wallet_by_id(
            event.current_transaction.sender.wallet_id
            if event.current_transaction.sender else event.current_transaction.receiver.wallet_id
        )
        webhooks = self._webhook_repository.get_webhooks_by_type(
            user_id=transaction_wallet.user_id,
            event_type=WebhookType.TransactionUpdate
        )

        for webhook in webhooks:
            self._handle_single_endpoint(
                webhook=webhook,
                event=event
            )
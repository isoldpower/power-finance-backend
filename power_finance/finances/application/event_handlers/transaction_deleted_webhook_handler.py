from finances.domain.entities import WebhookType
from finances.domain.events import TransactionDeletedEvent
from finances.infrastructure.integrations import WebhookDispatcher

from .event_webhook_handler import EventWebhookHandler
from ..interfaces import (
    WebhookRepository,
    WalletRepository,
    WebhookDeliveryRepository,
    EventPayloadFactory,
    EventBus, WebhookPayloadRepository,
)


class TransactionDeletedWebhookHandler(EventWebhookHandler):
    _webhook_repository: WebhookRepository
    _wallet_repository: WalletRepository
    _payload_factory: EventPayloadFactory

    def __init__(
            self,
            webhook_repository: WebhookRepository,
            delivery_repository: WebhookDeliveryRepository,
            payload_repository: WebhookPayloadRepository,
            wallet_repository: WalletRepository,
            payload_factory: EventPayloadFactory,
            dispatcher: WebhookDispatcher,
            event_bus: EventBus,
    ):
        super().__init__(
            event_type=WebhookType.TransactionDelete,
            delivery_repository=delivery_repository,
            dispatcher=dispatcher,
            event_bus=event_bus,
            payload_repository=payload_repository,
        )

        self._payload_factory = payload_factory
        self._webhook_repository = webhook_repository
        self._wallet_repository = wallet_repository

    def __call__(self, event: TransactionDeletedEvent) -> None:
        transaction_wallet = self._wallet_repository.get_wallet_by_id(
            event.sender.wallet_id
            if event.sender else event.receiver.wallet_id
        )
        webhooks = self._webhook_repository.get_webhooks_by_type(
            user_id=transaction_wallet.user_id,
            event_type=WebhookType.TransactionDelete
        )

        for webhook in webhooks:
            request_body = self._payload_factory.from_transaction_deleted(event)
            self.handle_dispatch_webhook_delivery(
                webhook=webhook,
                event=event,
                request_body=request_body,
            )
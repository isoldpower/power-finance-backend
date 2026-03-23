from django.db import transaction

from finances.domain.entities import WebhookType, Webhook
from finances.domain.events import TransactionCreatedEvent
from finances.infrastructure.integrations import WebhookDispatcher

from ..interfaces import (
    WebhookRepository, WalletRepository,
)
from ..interfaces import (
    WebhookDeliveryRepository,
    CreateWebhookDeliveryData,
    CreateWebhookDeliveryAttemptData,
    FinalizeWebhookDeliveryAttemptData,
    EventPayloadFactory,
)


class TransactionCreatedWebhookHandler:
    _webhook_repository: WebhookRepository
    _delivery_repository: WebhookDeliveryRepository

    def __init__(
            self,
            webhook_repository: WebhookRepository,
            delivery_repository: WebhookDeliveryRepository,
            wallet_repository: WalletRepository,
            payload_factory: EventPayloadFactory,
            dispatcher: WebhookDispatcher
    ):
        self._webhook_repository = webhook_repository
        self._delivery_repository = delivery_repository
        self._wallet_repository = wallet_repository
        self._payload_factory = payload_factory
        self._dispatcher = dispatcher

    @transaction.atomic
    def _handle_webhook_delivery(self, webhook: Webhook, event: TransactionCreatedEvent):
        request_body = self._payload_factory.from_transaction_created(event)
        delivery = self._delivery_repository.create_delivery(CreateWebhookDeliveryData(
            endpoint_id=webhook.id,
            event_id=event.event_id,
            event_type=WebhookType.TransactionCreate,
        ))

        request_data = self._dispatcher.get_request_data(
            webhook=webhook,
            event_type=WebhookType.TransactionCreate,
            payload=request_body,
        )
        delivery_attempt = self._delivery_repository.create_delivery_attempt(CreateWebhookDeliveryAttemptData(
            delivery_id=delivery.id,
            request_headers=request_data.request_headers,
            request_body=request_data.request_body,
        ))
        dispatch_result = self._dispatcher.dispatch_request(
            webhook=webhook,
            event_type=WebhookType.TransactionCreate,
            payload=request_body,
        )

        self._delivery_repository.finalize_delivery_attempt(FinalizeWebhookDeliveryAttemptData(
            attempt_id=delivery_attempt.id,
            response_status=dispatch_result.status_code,
            response_body=dispatch_result.response_body,
            error_message=dispatch_result.error_message,
        ))

    def __call__(self, event: TransactionCreatedEvent) -> None:
        transaction_wallet = self._wallet_repository.get_wallet_by_id(
            event.sender.wallet_id if event.sender else event.receiver.wallet_id
        )
        webhooks = self._webhook_repository.get_webhooks_by_type(
            user_id=transaction_wallet.user_id,
            event_type=WebhookType.TransactionCreate
        )

        for webhook in webhooks:
            self._handle_webhook_delivery(webhook, event)
import asyncio
import logging
from finances.domain.entities import WebhookType
from finances.domain.events import TransactionCreatedEvent
from finances.infrastructure.integrations import WebhookDispatcher

from .event_webhook_handler import EventWebhookHandler
from ..interfaces import (
    WebhookRepository,
    WalletRepository,
    WebhookDeliveryRepository,
    EventPayloadFactory,
    EventBus,
    WebhookPayloadRepository,
)



logger = logging.getLogger(__name__)


class TransactionCreatedWebhookHandler(EventWebhookHandler):
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
            event_type=WebhookType.TransactionCreate,
            delivery_repository=delivery_repository,
            payload_repository=payload_repository,
            event_bus=event_bus,
            dispatcher=dispatcher,
        )

        self._webhook_repository = webhook_repository
        self._wallet_repository = wallet_repository
        self._payload_factory = payload_factory

    async def __call__(self, event: TransactionCreatedEvent) -> None:
        logger.info("TransactionCreatedWebhookHandler: Received TransactionCreatedEvent (Event ID: %s)", event.event_id)
        webhooks = await self._webhook_repository.get_webhooks_by_type(
            user_id=event.user_id,
            event_type=WebhookType.TransactionCreate
        )

        await asyncio.gather(*[
            self.handle_dispatch_webhook_delivery(
                webhook=webhook,
                event_id=event.event_id,
                request_body=self._payload_factory.from_transaction_created(event),
            ) for webhook in webhooks
        ])

import logging
from uuid import UUID

from finances.domain.entities import Webhook, WebhookType, WebhookPayload
from finances.domain.events import EventCollector
from finances.infrastructure.integrations import WebhookDispatcher

from ..dtos import WebhookDeliveryDTO
from ..interfaces import (
    WebhookDeliveryRepository,
    WebhookPayloadRepository,
    CreateWebhookDeliveryData,
    EventBus,
)
from ..db_utils import aatomic


logger = logging.getLogger(__name__)


class EventWebhookHandler:
    def __init__(
            self,
            event_type: WebhookType,
            delivery_repository: WebhookDeliveryRepository,
            payload_repository: WebhookPayloadRepository,
            event_bus: EventBus,
            dispatcher: WebhookDispatcher,
    ):
        self._event_bus = event_bus
        self._delivery_repository = delivery_repository
        self._payload_repository = payload_repository
        self._event_type = event_type
        self._event_collector = EventCollector()
        self._dispatcher = dispatcher

    async def handle_dispatch_webhook_delivery(
            self,
            webhook: Webhook,
            event_id: UUID,
            request_body: dict
    ) -> WebhookDeliveryDTO:
        logger.info(
            "EventWebhookHandler: Handling webhook delivery for Event ID: %s, Webhook ID: %s",
            event_id, webhook.id
        )
        async with aatomic():
            request_stamp = self._dispatcher.get_request_data(
                webhook=webhook,
                event_type=self._event_type.value,
                payload=request_body
            )
            delivery = await self._delivery_repository.create_delivery(CreateWebhookDeliveryData(
                endpoint_id=webhook.id,
                event_id=event_id,
            ))
            payload = WebhookPayload.create(
                delivery_id=delivery.id,
                payload=request_stamp.request_body,
                headers=request_stamp.request_headers,
            )
            await self._payload_repository.write_delivery_payload(payload)

        logger.info(
            "EventWebhookHandler: Successfully created delivery (ID: %s) for Event ID: %s",
            delivery.id, event_id
        )
        return delivery
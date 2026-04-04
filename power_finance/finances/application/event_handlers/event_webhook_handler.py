from uuid import UUID
from django.db import transaction

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

    @transaction.atomic
    def handle_dispatch_webhook_delivery(
            self,
            webhook: Webhook,
            event_id: UUID,
            request_body: dict
    ) -> WebhookDeliveryDTO:

        request_stamp = self._dispatcher.get_request_data(
            webhook=webhook,
            event_type=self._event_type,
            payload=request_body
        )
        delivery = self._delivery_repository.create_delivery(CreateWebhookDeliveryData(
            endpoint_id=webhook.id,
            event_id=event_id,
        ))
        payload = WebhookPayload.create(
            delivery_id=delivery.id,
            payload=request_stamp.request_body,
            headers=request_stamp.request_headers,
        )
        self._payload_repository.write_delivery_payload(payload)

        return delivery
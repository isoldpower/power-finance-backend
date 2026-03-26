from uuid import UUID
from django.db import transaction

from finances.domain.entities import Webhook, WebhookType
from finances.infrastructure.integrations import WebhookDispatcher

from ..dtos import WebhookDeliveryDTO
from ..interfaces import (
    WebhookDeliveryRepository,
    CreateWebhookDeliveryData,
    CreateWebhookDeliveryAttemptData,
    FinalizeWebhookDeliveryAttemptData, MessageResponse,
)


class EventWebhookHandler:
    def __init__(
            self,
            event_type: WebhookType,
            delivery_repository: WebhookDeliveryRepository,
            dispatcher: WebhookDispatcher
    ):
        self._delivery_repository = delivery_repository
        self._dispatcher = dispatcher
        self._event_type = event_type

    @transaction.atomic
    def handle_dispatch_webhook_delivery(
            self,
            webhook: Webhook,
            event_id: UUID,
    ) -> WebhookDeliveryDTO:
        delivery = self._delivery_repository.create_delivery(CreateWebhookDeliveryData(
            endpoint_id=webhook.id,
            event_id=event_id,
        ))

        return delivery

    def handle_webhook_delivery_attempt(
            self,
            webhook: Webhook,
            delivery_id: UUID,
            request_body: dict,
    ):
        with transaction.atomic():
            request_data = self._dispatcher.get_request_data(
                webhook=webhook,
                event_type=self._event_type.value,
                payload=request_body,
            )
            delivery_attempt = self._delivery_repository.create_delivery_attempt(CreateWebhookDeliveryAttemptData(
                delivery_id=delivery_id,
                request_headers=request_data.request_headers,
                request_body=request_data.request_body,
            ))

        try:
            dispatch_result = self._dispatcher.dispatch_request(
                webhook=webhook,
                event_type=self._event_type,
                payload=request_body,
            )
        except Exception as exception:
            dispatch_result = MessageResponse(
                status_code=-1,
                response_body=None,
                response_headers=None,
                error_message=str(exception) or "Unknown dispatch error",
            )

        with transaction.atomic():
            self._delivery_repository.finalize_delivery_attempt(FinalizeWebhookDeliveryAttemptData(
                attempt_id=delivery_attempt.id,
                response_status=dispatch_result.status_code,
                response_body=dispatch_result.response_body,
                error_message=dispatch_result.error_message,
            ))
            self._delivery_repository.finalize_delivery(delivery_id=delivery_id)
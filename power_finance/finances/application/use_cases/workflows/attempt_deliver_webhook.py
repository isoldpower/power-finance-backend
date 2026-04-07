from datetime import timedelta
from uuid import UUID
import requests
from django.db import transaction

from finances.domain.entities import Webhook
from finances.domain.events import (
    WebhookDeliveryStatus,
    WebhookDeliveryStatusChangedEvent,
)
from finances.infrastructure.integrations import (
    WebhookDispatcher,
    HttpSender,
    RequestStamp,
)

from ..use_case_base import UseCaseEvently
from ..decorators import handle_evently_command_transaction
from ...bootstrap import get_repository_registry
from ...interfaces import (
    CreateWebhookDeliveryAttemptData,
    MessageResponse,
)


class WebhookDeliveryAttemptHandler(UseCaseEvently):
    def __init__(self):
        super().__init__()

        registry = get_repository_registry()
        self._dispatcher = WebhookDispatcher(HttpSender())
        self._payload_repository = registry.payload_repository
        self._delivery_repository = registry.delivery_repository

    @handle_evently_command_transaction()
    def handle(
            self,
            webhook: Webhook,
            delivery_id: UUID,
    ):
        with transaction.atomic():
            payload = self._payload_repository.get_delivery_payload(delivery_id=delivery_id)
            self._delivery_repository.create_delivery_attempt(CreateWebhookDeliveryAttemptData(
                delivery_id=delivery_id,
                request_headers=payload.headers,
                request_body=payload.payload,
            ))
            self._delivery_repository.mark_delivery_in_progress(delivery_id=delivery_id)

        try:
            dispatch_result = self._dispatcher.dispatch_request(
                webhook=webhook,
                request_stamp=RequestStamp(
                    request_body=payload.payload,
                    request_headers=payload.headers,
                ),
            )
        except (requests.Timeout, requests.ConnectionError) as exception:
            dispatch_result = MessageResponse(
                status_code=-1,
                response_body=None,
                response_headers=None,
                error_message=str(exception) or "Transient dispatch error",
            )
        except Exception as exception:
            dispatch_result = MessageResponse(
                status_code=-1,
                response_body=None,
                response_headers=None,
                error_message=str(exception) or "Unknown dispatch error",
            )

        with transaction.atomic():
            if 200 <= dispatch_result.status_code < 300:
                status = WebhookDeliveryStatus.SUCCESS
                self._delivery_repository.mark_delivery_success(delivery_id=delivery_id)
            elif dispatch_result.status_code == 429 or dispatch_result.status_code >= 500 or dispatch_result.status_code == -1:
                status = WebhookDeliveryStatus.RETRY_SCHEDULED
                self._delivery_repository.mark_delivery_retry_scheduled(
                    delivery_id=delivery_id,
                    error_message=dispatch_result.error_message,
                    retry_in=timedelta(minutes=1),
                )
            else:
                status = WebhookDeliveryStatus.FAILED
                self._delivery_repository.mark_delivery_failed(
                    delivery_id=delivery_id,
                    error_message=dispatch_result.error_message,
                )

            self.event_collector.collect(WebhookDeliveryStatusChangedEvent(
                delivery_id=delivery_id,
                endpoint_id=webhook.id,
                user_id=webhook.user_id,
                status=status,
            ))
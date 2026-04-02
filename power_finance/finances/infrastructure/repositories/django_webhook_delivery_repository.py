from uuid import UUID

from django.utils import timezone
from django.db.models import Max

from finances.application.interfaces import (
    WebhookDeliveryRepository,
    CreateWebhookDeliveryData,
    CreateWebhookDeliveryAttemptData,
    FinalizeWebhookDeliveryAttemptData,
)
from finances.application.dtos import WebhookDeliveryAttemptDTO, WebhookDeliveryDTO

from ..mappers import WebhookDeliveryMapper
from ..orm import WebhookDeliveryAttemptModel, WebhookDeliveryModel, WebhookDeliveryStatusChoices


class DjangoWebhookDeliveryRepository(WebhookDeliveryRepository):
    def get_delivery_by_id(
            self,
            webhook_id: UUID,
            event_id: UUID,
            user_id: UUID,
    ) -> WebhookDeliveryDTO:
        delivery = WebhookDeliveryModel.objects.get(
            endpoint_id=webhook_id,
            event_id=event_id,
            user_id=user_id,
        )

        return WebhookDeliveryMapper.delivery_to_dto(delivery)

    def create_delivery(
            self,
            data: CreateWebhookDeliveryData
    ) -> WebhookDeliveryDTO:
        created_delivery = WebhookDeliveryModel.objects.create(
            endpoint_id=data.endpoint_id,
            event_id=data.event_id,
        )

        return WebhookDeliveryMapper.delivery_to_dto(created_delivery)

    def create_delivery_attempt(
            self,
            data: CreateWebhookDeliveryAttemptData
    ) -> WebhookDeliveryAttemptDTO:
        last_attempt_number = (WebhookDeliveryAttemptModel.objects
            .filter(delivery_id=data.delivery_id)
            .aggregate(max_attempt=Max('attempt_number'))
            .get("max_attempt") or 0)

        created_attempt = WebhookDeliveryAttemptModel.objects.create(
            delivery_id=data.delivery_id,
            attempt_number=last_attempt_number + 1,
            request_headers=data.request_headers,
            request_body=data.request_body,
        )

        return WebhookDeliveryMapper.attempt_to_dto(created_attempt)

    def finalize_delivery_attempt(
            self,
            data: FinalizeWebhookDeliveryAttemptData
    ) -> WebhookDeliveryAttemptDTO:
        attempt = WebhookDeliveryAttemptModel.objects.get(
            id=data.attempt_id,
            finished_at__isnull=True,
        )

        attempt.error_message = data.error_message
        attempt.response_body = data.response_body
        attempt.response_status = data.response_status
        attempt.finished_at = timezone.now()

        attempt.save(
            update_fields=['error_message', 'response_status', 'response_body', 'finished_at']
        )
        return WebhookDeliveryMapper.attempt_to_dto(attempt)

    def finalize_delivery(
            self,
            delivery_id: UUID,
    ) -> WebhookDeliveryDTO:
        delivery = WebhookDeliveryModel.objects.get(id=delivery_id)
        first_successful_attempt = (WebhookDeliveryAttemptModel.objects
            .filter(
                delivery_id=delivery_id,
                response_status__isnull=False,
                response_status__gte=200,
                response_status__lt=300,
            )
            .order_by('-attempt_number')
            .first())

        if first_successful_attempt:
            delivery.status = WebhookDeliveryStatusChoices.DELIVERED
            delivery.delivered_at = first_successful_attempt.finished_at
            delivery.next_retry_at = None
        else:
            delivery.status = WebhookDeliveryStatusChoices.FAILED_PERMANENTLY
            delivery.delivered_at = None
            delivery.next_retry_at = None

        delivery.save(
            update_fields=['status', 'delivered_at', 'next_retry_at', 'updated_at']
        )
        return WebhookDeliveryMapper.delivery_to_dto(delivery)
from datetime import timedelta
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

    def get_deliveries_to_retry(self, limit: int) -> list[WebhookDeliveryDTO]:
        deliveries_to_retry = (WebhookDeliveryModel.objects
            .filter(
                status=WebhookDeliveryStatusChoices.RETRY_SCHEDULED.value,
                next_retry_at__lte=timezone.now(),
            )[:limit])

        return [WebhookDeliveryMapper.delivery_to_dto(delivery) for delivery in deliveries_to_retry]

    def mark_delivery_in_progress(self, delivery_id: UUID) -> WebhookDeliveryDTO:
        delivery = WebhookDeliveryModel.objects.get(id=delivery_id)

        delivery.status = WebhookDeliveryStatusChoices.IN_PROGRESS
        delivery.save(update_fields=['status', 'updated_at'])

        return WebhookDeliveryMapper.delivery_to_dto(delivery)

    def mark_delivery_success(self, delivery_id: UUID) -> WebhookDeliveryDTO:
        delivery = WebhookDeliveryModel.objects.get(id=delivery_id)

        delivery.status = WebhookDeliveryStatusChoices.DELIVERED
        delivery.delivered_at = timezone.now()
        delivery.next_retry_at = None
        delivery.save(update_fields=['status', 'delivered_at', 'next_retry_at', 'updated_at'])

        return WebhookDeliveryMapper.delivery_to_dto(delivery)

    def mark_delivery_retry_scheduled(
            self,
            delivery_id: UUID,
            error_message: str | None,
            retry_in: timedelta,
    ) -> WebhookDeliveryDTO:
        delivery = WebhookDeliveryModel.objects.get(id=delivery_id)

        delivery.status = WebhookDeliveryStatusChoices.RETRY_SCHEDULED
        delivery.next_retry_at = timezone.now() + retry_in
        delivery.save(update_fields=['status', 'next_retry_at', 'updated_at'])

        return WebhookDeliveryMapper.delivery_to_dto(delivery)

    def mark_delivery_failed(self, delivery_id: UUID, error_message: str | None) -> WebhookDeliveryDTO:
        delivery = WebhookDeliveryModel.objects.get(id=delivery_id)

        delivery.status = WebhookDeliveryStatusChoices.FAILED_PERMANENTLY
        delivery.next_retry_at = None
        delivery.delivered_at = None
        delivery.save(update_fields=['status', 'next_retry_at', 'delivered_at', 'updated_at'])

        return WebhookDeliveryMapper.delivery_to_dto(delivery)

from finances.application.dtos import WebhookDeliveryDTO, WebhookDeliveryAttemptDTO
from finances.infrastructure.orm import WebhookDeliveryModel, WebhookDeliveryAttemptModel

from .update_mapper import UpdateMapper


class WebhookDeliveryMapper:
    DELIVERY_ATTEMPT_EDITABLE_MAP: list[tuple[str, str]] = [
        ('request_headers', 'request_headers'),
        ('request_body', 'request_body'),
        ('response_status', 'response_status'),
        ('response_body', 'response_body'),
        ('error_message', 'error_message'),
        ('finished_at', 'finished_at'),
    ]

    @staticmethod
    def delivery_to_dto(model: WebhookDeliveryModel) -> WebhookDeliveryDTO:
        return WebhookDeliveryDTO(
            id=model.id,
            status=model.status,
            endpoint_id=model.endpoint_id,
            event_id=model.event_id,
            updated_at=model.updated_at,
            delivered_at=model.delivered_at,
            next_retry_at=model.next_retry_at,
        )

    @staticmethod
    def attempt_to_dto(model: WebhookDeliveryAttemptModel) -> WebhookDeliveryAttemptDTO:
        return WebhookDeliveryAttemptDTO(
            id=model.id,
            delivery_id=model.delivery_id,
            attempt_number=model.attempt_number,
            request_headers=model.request_headers,
            request_body=model.request_body,
            response_status=model.response_status,
            response_body=model.response_body,
            error_message=model.error_message,
            started_at=model.started_at,
            finished_at=model.finished_at,
        )

    @staticmethod
    def update_attempt(
        model: WebhookDeliveryAttemptModel,
        dto: WebhookDeliveryAttemptDTO
    ) -> WebhookDeliveryAttemptModel:
        return UpdateMapper[WebhookDeliveryAttemptModel, WebhookDeliveryAttemptDTO].update_model(
            model=model,
            entity=dto,
            update_fields=WebhookDeliveryMapper.DELIVERY_ATTEMPT_EDITABLE_MAP,
            replace=False
        )

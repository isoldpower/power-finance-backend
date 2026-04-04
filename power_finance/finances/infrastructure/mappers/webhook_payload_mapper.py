from finances.infrastructure.orm import WebhookPayloadModel
from finances.domain.entities import WebhookPayload

from .update_mapper import UpdateMapper


class WebhookPayloadMapper:
    PAYLOAD_EDITABLE_MAP: list[tuple[str, str]] = [
        ('hash', 'hash'),
        ('delivery_id', 'delivery_id'),
        ('payload', 'payload'),
    ]

    @staticmethod
    def to_domain(model: WebhookPayloadModel) -> WebhookPayload:
        return WebhookPayload(
            id=model.id,
            delivery_id=model.delivery_id,
            payload=model.payload,
        )

    @staticmethod
    def update_model(
        model: WebhookPayloadModel,
        entity: WebhookPayload,
    ) -> WebhookPayloadModel:
        return UpdateMapper[WebhookPayloadModel, WebhookPayload].update_model(
            model=model,
            entity=entity,
            update_fields=WebhookPayloadMapper.PAYLOAD_EDITABLE_MAP,
            replace=False
        )

from uuid import UUID

from finances.application.interfaces import WebhookPayloadRepository
from finances.domain.entities import WebhookPayload

from ..mappers import WebhookPayloadMapper
from ..orm import WebhookPayloadModel


class DjangoWebhookPayloadRepository(WebhookPayloadRepository):
    def write_delivery_payload(self, entity: WebhookPayload) -> WebhookPayload:
        created_model = WebhookPayloadModel.objects.create(delivery_id=entity.delivery_id)
        synced_model = WebhookPayloadMapper.update_model(created_model, entity)
        synced_model.save()

        return WebhookPayloadMapper.to_domain(synced_model)

    def get_delivery_payload(self, delivery_id: UUID) -> WebhookPayload:
        requested_payload = WebhookPayloadModel.objects.get(delivery_id=delivery_id)

        return WebhookPayloadMapper.to_domain(requested_payload)

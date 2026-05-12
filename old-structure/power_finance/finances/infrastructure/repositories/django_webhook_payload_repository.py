from uuid import UUID

from finances.application.interfaces import WebhookPayloadRepository
from finances.domain.entities import WebhookPayload

from ..mappers import WebhookPayloadMapper
from ..orm import WebhookPayloadModel


class DjangoWebhookPayloadRepository(WebhookPayloadRepository):
    async def write_delivery_payload(self, entity: WebhookPayload) -> WebhookPayload:
        created_model = WebhookPayloadModel()
        WebhookPayloadMapper.update_model(created_model, entity)
        await created_model.asave()

        return WebhookPayloadMapper.to_domain(created_model)

    async def get_delivery_payload(self, delivery_id: UUID) -> WebhookPayload:
        requested_payload = await WebhookPayloadModel.objects.aget(delivery_id=delivery_id)

        return WebhookPayloadMapper.to_domain(requested_payload)

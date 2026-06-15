from datetime import UTC

from kafka_messages import WebhookEndpointCreated

from data_read_core.shared.kafka_updates import Effect, EventMessage
from data_read_core.shared.postgres_orm import WebhookReadModel

from .._logger_shortcuts import log_webhook_postgres_created
from .._utilities import decode_payload, handle_database_errors


class CreateWebhookReadModel(Effect):
    """Projects the endpoint config WITHOUT the secret — reads never expose
    it; only the webhook-service consumes it."""

    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, WebhookEndpointCreated)
        await handle_database_errors(
            self._create_webhook,
            payload,
            resource_id=payload.webhook_id,
        )

    async def _create_webhook(self, payload: WebhookEndpointCreated) -> WebhookReadModel:
        created_webhook = await WebhookReadModel.objects.acreate(
            id=payload.webhook_id,
            user_id=payload.user_id,
            title=payload.title,
            url=payload.url,
            is_active=True,
            created_at=payload.created_at.ToDatetime(tzinfo=UTC),
            updated_at=None,
        )
        log_webhook_postgres_created(payload.webhook_id)

        return created_webhook

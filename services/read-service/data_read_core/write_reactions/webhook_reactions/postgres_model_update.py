from datetime import UTC

from kafka_messages import WebhookEndpointUpdated

from data_read_core.shared.kafka_updates import Effect, EventMessage
from data_read_core.shared.postgres_orm import WebhookReadModel

from .._logger_shortcuts import log_webhook_postgres_updated
from .._utilities import decode_payload, handle_database_errors


class UpdateWebhookReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, WebhookEndpointUpdated)
        await handle_database_errors(
            self._update_webhook,
            payload,
            resource_id=payload.webhook_id,
        )

    async def _update_webhook(self, payload: WebhookEndpointUpdated) -> int:
        updated = await WebhookReadModel.objects.filter(id=payload.webhook_id).aupdate(
            title=payload.title,
            url=payload.url,
            updated_at=payload.updated_at.ToDatetime(tzinfo=UTC),
        )
        log_webhook_postgres_updated(payload.webhook_id, updated)

        return updated

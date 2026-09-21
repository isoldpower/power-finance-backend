from kafka_consumer_py import Effect, EventMessage
from kafka_messages import WebhookEndpointDeleted

from data_read_core.shared.postgres_orm import WebhookReadModel

from .._logger_shortcuts import log_webhook_postgres_removed
from .._utilities import decode_payload, handle_database_errors


class RemoveWebhookReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, WebhookEndpointDeleted)
        await handle_database_errors(
            self._remove_webhook,
            payload,
            resource_id=payload.webhook_id,
        )

    async def _remove_webhook(self, payload: WebhookEndpointDeleted) -> int:
        deleted_count, _ = await WebhookReadModel.objects.filter(
            id=payload.webhook_id,
        ).adelete()
        log_webhook_postgres_removed(payload.webhook_id, deleted_count)

        return deleted_count

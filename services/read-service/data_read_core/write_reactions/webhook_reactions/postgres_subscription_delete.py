from kafka_messages import WebhookSubscriptionRemoved

from data_read_core.shared.kafka_updates import Effect, EventMessage
from data_read_core.shared.postgres_orm import WebhookSubscriptionReadModel

from .._logger_shortcuts import log_webhook_subscription_postgres_removed
from .._utilities import decode_payload, handle_database_errors


class RemoveWebhookSubscriptionReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, WebhookSubscriptionRemoved)
        await handle_database_errors(
            self._remove_subscription,
            payload,
            resource_id=payload.subscription_id,
        )

    async def _remove_subscription(self, payload: WebhookSubscriptionRemoved) -> int:
        deleted_count, _ = await WebhookSubscriptionReadModel.objects.filter(
            id=payload.subscription_id,
        ).adelete()
        log_webhook_subscription_postgres_removed(payload.subscription_id, deleted_count)

        return deleted_count

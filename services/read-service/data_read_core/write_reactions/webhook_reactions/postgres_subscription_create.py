from datetime import UTC

from kafka_messages import WebhookSubscriptionAdded

from data_read_core.shared.kafka_updates import Effect, EventMessage
from data_read_core.shared.postgres_orm import WebhookSubscriptionReadModel

from .._logger_shortcuts import log_webhook_subscription_postgres_created
from .._utilities import decode_payload, handle_database_errors


class CreateWebhookSubscriptionReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, WebhookSubscriptionAdded)
        await handle_database_errors(
            self._create_subscription,
            payload,
            resource_id=payload.subscription_id,
        )

    async def _create_subscription(
        self, payload: WebhookSubscriptionAdded
    ) -> WebhookSubscriptionReadModel:
        created_subscription = await WebhookSubscriptionReadModel.objects.acreate(
            id=payload.subscription_id,
            webhook_id=payload.webhook_id,
            user_id=payload.user_id,
            event_type=payload.event_type,
            is_active=True,
            created_at=payload.created_at.ToDatetime(tzinfo=UTC),
        )
        log_webhook_subscription_postgres_created(payload.subscription_id)

        return created_subscription

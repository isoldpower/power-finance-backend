from datetime import UTC

from google.protobuf.json_format import MessageToDict
from kafka_consumer_py import Effect, EventMessage
from kafka_messages import NotificationCreated

from data_read_core.shared.postgres_orm import NotificationReadModel

from .._logger_shortcuts import log_notification_postgres_created
from .._utilities import decode_payload, handle_database_errors


class CreateNotificationReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, NotificationCreated)
        await handle_database_errors(
            self._create_notification,
            payload,
            resource_id=payload.notification_id,
        )

    async def _create_notification(self, payload: NotificationCreated) -> NotificationReadModel:
        created_notification = await NotificationReadModel.objects.acreate(
            id=payload.notification_id,
            user_id=payload.user_id,
            short=payload.short,
            message=payload.message,
            payload=MessageToDict(payload.payload) if payload.HasField("payload") else None,
            is_read=False,
            created_at=payload.created_at.ToDatetime(tzinfo=UTC),
        )
        log_notification_postgres_created(payload.notification_id)

        return created_notification

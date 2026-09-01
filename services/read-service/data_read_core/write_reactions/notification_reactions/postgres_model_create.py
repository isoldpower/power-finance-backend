from datetime import UTC

from google.protobuf.json_format import MessageToDict
from kafka_consumer_py import Effect, EventMessage
from kafka_messages import NotificationCreated

from data_read_core.shared.postgres_orm import NotificationReadModel

from .._logger_shortcuts import log_notification_postgres_created
from .._utilities import decode_payload, handle_database_errors
from ._utilities import severity_from_proto


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
            title=payload.title,
            body=payload.body,
            payload=MessageToDict(payload.payload) if payload.HasField("payload") else None,
            severity=severity_from_proto(payload.severity),
            subject_type=payload.subject_type,
            subject_id=payload.subject_id,
            acknowledged_at=None,
            created_at=payload.created_at.ToDatetime(tzinfo=UTC),
        )
        log_notification_postgres_created(payload.notification_id)

        return created_notification

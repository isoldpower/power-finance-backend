from kafka_messages import NotificationDeleted

from data_read_core.shared.kafka_updates import Effect, EventMessage
from data_read_core.shared.postgres_orm import NotificationReadModel

from .._logger_shortcuts import log_notification_postgres_removed
from .._utilities import decode_payload, handle_database_errors


class RemoveNotificationReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, NotificationDeleted)
        await handle_database_errors(
            self._remove_notification,
            payload,
            resource_id=payload.notification_id,
        )

    async def _remove_notification(self, payload: NotificationDeleted) -> int:
        deleted_count, _ = await NotificationReadModel.objects.filter(
            id=payload.notification_id,
        ).adelete()
        log_notification_postgres_removed(payload.notification_id, deleted_count)

        return deleted_count

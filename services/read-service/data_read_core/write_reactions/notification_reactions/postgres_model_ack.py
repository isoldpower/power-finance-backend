from datetime import UTC

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import NotificationsAcknowledged

from data_read_core.shared.postgres_orm import NotificationReadModel

from .._logger_shortcuts import log_notification_postgres_acknowledged
from .._utilities import decode_payload, handle_database_errors


class AcknowledgeNotificationReadModels(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, NotificationsAcknowledged)
        await handle_database_errors(
            self._acknowledge_notifications,
            payload,
            resource_id=",".join(payload.notification_ids),
        )

    async def _acknowledge_notifications(self, payload: NotificationsAcknowledged) -> int:
        acknowledged_at = payload.acknowledged_at.ToDatetime(tzinfo=UTC)
        updated_notifications = await NotificationReadModel.objects.filter(
            id__in=list(payload.notification_ids),
            user_id=payload.user_id,
            acknowledged_at__isnull=True,
        ).aupdate(
            acknowledged_at=acknowledged_at,
            updated_at=acknowledged_at,
        )
        log_notification_postgres_acknowledged(
            list(payload.notification_ids),
            updated_notifications,
        )

        return updated_notifications

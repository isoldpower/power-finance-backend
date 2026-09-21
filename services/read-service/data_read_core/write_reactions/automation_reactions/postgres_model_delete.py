from datetime import UTC

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import AutomationDeleted

from data_read_core.shared.postgres_orm import AutomationReadModel

from .._logger_shortcuts import log_automation_postgres_deleted
from .._utilities import decode_payload, handle_database_errors


class RemoveAutomationReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, AutomationDeleted)
        await handle_database_errors(
            self._remove,
            payload,
            resource_id=payload.automation_id,
        )

    async def _remove(self, payload: AutomationDeleted) -> int:
        deleted_at = payload.deleted_at.ToDatetime(tzinfo=UTC)
        updated_at = await AutomationReadModel.objects.filter(
            id=payload.automation_id,
            user_id=payload.user_id,
            deleted_at__isnull=True,
        ).aupdate(
            deleted_at=deleted_at,
            updated_at=deleted_at,
            enabled=False,
        )

        log_automation_postgres_deleted(
            payload.automation_id,
            updated_at,
        )

        return updated_at

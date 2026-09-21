from datetime import UTC

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import AutomationDeleted

from data_read_core.shared.elasticsearch import (
    AUTOMATIONS_INDEX,
    SEARCHABLE_REFRESH,
    get_elasticsearch,
)

from .._logger_shortcuts import log_automation_elastic_removed
from .._utilities import decode_payload


class RemoveAutomationDocument(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, AutomationDeleted)
        deleted_at = payload.deleted_at.ToDatetime(tzinfo=UTC).isoformat()

        await (
            get_elasticsearch()
            .options(ignore_status=404)
            .update(
                index=AUTOMATIONS_INDEX,
                id=payload.automation_id,
                doc={
                    "deleted_at": deleted_at,
                    "updated_at": deleted_at,
                    "enabled": False,
                },
                refresh=SEARCHABLE_REFRESH,
            )
        )
        log_automation_elastic_removed(
            payload.automation_id,
            AUTOMATIONS_INDEX,
        )

from datetime import UTC

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import AutomationCreated, AutomationRan, AutomationUpdated

from data_read_core.shared.elasticsearch import (
    AUTOMATIONS_INDEX,
    SEARCHABLE_REFRESH,
    get_elasticsearch,
)

from .._logger_shortcuts import (
    log_automation_elastic_projected,
    log_automation_elastic_ran,
)
from .._utilities import decode_payload
from ._utilities import effects_of, filter_body_of


class IndexAutomationDocument(Effect):
    def __init__(
        self,
        payload_type: type[AutomationCreated] | type[AutomationUpdated] = AutomationCreated,
    ) -> None:
        self._payload_type = payload_type

    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, self._payload_type)
        is_creation = isinstance(payload, AutomationCreated)
        stamped_at = (payload.created_at if is_creation else payload.updated_at).ToDatetime(
            tzinfo=UTC
        )
        document = {
            "id": payload.automation_id,
            "user_id": payload.user_id,
            "name": payload.name,
            "icon": payload.icon,
            "enabled": payload.enabled,
            "trigger_type": payload.trigger.trigger_type,
            "trigger_event": payload.trigger.event,
            "trigger_schedule": payload.trigger.schedule,
            "filter_body": filter_body_of(payload.trigger.filter_body_json),
            "effects": effects_of(payload.effects),
            "updated_at": None if is_creation else stamped_at.isoformat(),
        }

        if is_creation:
            document["created_at"] = stamped_at.isoformat()
            document["runs"] = 0
            document["last_run_at"] = None
            document["deleted_at"] = None

        await get_elasticsearch().update(
            index=AUTOMATIONS_INDEX,
            id=payload.automation_id,
            doc=document,
            doc_as_upsert=True,
            refresh=SEARCHABLE_REFRESH,
        )
        log_automation_elastic_projected(
            payload.automation_id,
            AUTOMATIONS_INDEX,
            is_creation,
        )


class RecordAutomationRunDocument(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, AutomationRan)

        await (
            get_elasticsearch()
            .options(ignore_status=404)
            .update(
                index=AUTOMATIONS_INDEX,
                id=payload.automation_id,
                doc={
                    "runs": payload.runs,
                    "last_run_at": payload.last_run_at.ToDatetime(tzinfo=UTC).isoformat(),
                },
                refresh=SEARCHABLE_REFRESH,
            )
        )
        log_automation_elastic_ran(
            payload.automation_id,
            AUTOMATIONS_INDEX,
            payload.runs,
        )

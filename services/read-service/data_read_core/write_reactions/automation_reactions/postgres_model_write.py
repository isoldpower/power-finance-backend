from datetime import UTC

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import AutomationCreated, AutomationRan, AutomationUpdated

from data_read_core.shared.postgres_orm import AutomationReadModel

from .._logger_shortcuts import (
    log_automation_postgres_projected,
    log_automation_postgres_ran,
)
from .._utilities import decode_payload, handle_database_errors
from ._utilities import effects_of, filter_body_of


class ProjectAutomationReadModel(Effect):
    def __init__(
        self,
        payload_type: type[AutomationCreated] | type[AutomationUpdated] = AutomationCreated,
    ) -> None:
        self._payload_type = payload_type

    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, self._payload_type)
        await handle_database_errors(
            self._project,
            payload,
            resource_id=payload.automation_id,
        )

    async def _project(self, payload: AutomationCreated | AutomationUpdated) -> None:
        is_creation = isinstance(payload, AutomationCreated)
        stamped_at = (payload.created_at if is_creation else payload.updated_at).ToDatetime(
            tzinfo=UTC
        )
        fields = {
            "user_id": payload.user_id,
            "name": payload.name,
            "icon": payload.icon,
            "enabled": payload.enabled,
            "trigger_type": payload.trigger.trigger_type,
            "trigger_event": payload.trigger.event,
            "trigger_schedule": payload.trigger.schedule,
            "filter_body": filter_body_of(payload.trigger.filter_body_json),
            "effects": effects_of(payload.effects),
        }

        if not is_creation:
            fields["updated_at"] = stamped_at

        await AutomationReadModel.objects.aupdate_or_create(
            id=payload.automation_id,
            defaults=fields,
            create_defaults={**fields, "created_at": stamped_at},
        )
        log_automation_postgres_projected(
            payload.automation_id,
            is_creation,
        )


class RecordAutomationRun(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, AutomationRan)
        await handle_database_errors(
            self._record,
            payload,
            resource_id=payload.automation_id,
        )

    async def _record(self, payload: AutomationRan) -> None:
        await AutomationReadModel.objects.filter(
            id=payload.automation_id,
            user_id=payload.user_id,
        ).aupdate(
            runs=payload.runs,
            last_run_at=payload.last_run_at.ToDatetime(tzinfo=UTC),
        )

        log_automation_postgres_ran(payload.automation_id, payload.runs)

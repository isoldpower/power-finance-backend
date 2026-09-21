from datetime import UTC

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import ActionResolved

from data_read_core.shared.postgres_orm import ActionReadModel, ActionStatus

from .._logger_shortcuts import log_action_postgres_resolved
from .._utilities import decode_payload, handle_database_errors
from ._utilities import status_of


class ResolveActionReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, ActionResolved)
        await handle_database_errors(
            self._resolve_action,
            payload,
            resource_id=payload.action_id,
        )

    async def _resolve_action(self, payload: ActionResolved) -> int:
        resolved_at = payload.resolved_at.ToDatetime(tzinfo=UTC)
        updated_actions = await ActionReadModel.objects.filter(
            id=payload.action_id,
            user_id=payload.user_id,
            status=ActionStatus.PENDING,
        ).aupdate(
            status=status_of(payload.status),
            resolved_at=resolved_at,
            updated_at=resolved_at,
            resolutions=[],
        )

        log_action_postgres_resolved(payload.action_id, updated_actions)

        return updated_actions

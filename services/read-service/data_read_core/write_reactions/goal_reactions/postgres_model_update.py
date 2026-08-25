from datetime import UTC
from decimal import Decimal

from kafka_messages import GoalUpdated

from data_read_core.shared.kafka_updates import Effect, EventMessage
from data_read_core.shared.postgres_orm import GoalReadModel

from .._logger_shortcuts import log_goal_postgres_updated
from .._utilities import decode_payload, handle_database_errors


class UpdateGoalReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        event_payload = decode_payload(event, GoalUpdated)
        await handle_database_errors(
            self._update_goal,
            event_payload,
            resource_id=event_payload.goal_id,
        )

    async def _update_goal(self, payload: GoalUpdated) -> None:
        updated_row = await GoalReadModel.objects.filter(id=payload.goal_id).aupdate(
            title=payload.new_title,
            updated_at=payload.updated_at.ToDatetime(tzinfo=UTC),
            target=Decimal(payload.target or "0"),
            finish_at=(
                payload.finish_at.ToDatetime(tzinfo=UTC) if payload.HasField("finish_at") else None
            ),
            url=payload.url or None,
        )

        log_goal_postgres_updated(payload.goal_id, updated_row)

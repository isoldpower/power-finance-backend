from datetime import UTC

from kafka_messages import GoalDeleted

from data_read_core.shared.kafka_updates import EventMessage
from data_read_core.shared.kafka_updates.processing import Effect
from data_read_core.shared.postgres_orm import GoalReadModel

from .._logger_shortcuts import log_goal_postgres_removed
from .._utilities import decode_payload, handle_database_errors


class RemoveGoalReadModel(Effect):
    """Close the goal projection rather than dropping the row: it leaves lists but
    stays queryable by id, so the transactions that funded it still resolve a name."""

    async def apply(self, event: EventMessage) -> None:
        event_payload = decode_payload(event, GoalDeleted)
        await handle_database_errors(
            self._close_goal,
            event_payload,
            resource_id=event_payload.goal_id,
        )

    async def _close_goal(self, payload: GoalDeleted) -> None:
        deleted_at = payload.deleted_at.ToDatetime(tzinfo=UTC)
        closed_goal = await GoalReadModel.objects.filter(id=payload.goal_id).aupdate(
            deleted_at=deleted_at,
            updated_at=deleted_at,
        )

        log_goal_postgres_removed(payload.goal_id, closed_goal)

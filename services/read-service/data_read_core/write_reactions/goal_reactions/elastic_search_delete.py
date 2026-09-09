from datetime import UTC

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import GoalDeleted

from data_read_core.shared.elasticsearch import (
    GOALS_INDEX,
    SEARCHABLE_REFRESH,
    get_elasticsearch,
)

from .._logger_shortcuts import log_goal_elastic_removed
from .._utilities import decode_payload


class RemoveGoalDocument(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, GoalDeleted)
        deleted_at = payload.deleted_at.ToDatetime(tzinfo=UTC).isoformat()

        await (
            get_elasticsearch()
            .options(ignore_status=404)
            .update(
                index=GOALS_INDEX,
                id=payload.goal_id,
                doc={"deleted_at": deleted_at, "updated_at": deleted_at},
                refresh=SEARCHABLE_REFRESH,
            )
        )
        log_goal_elastic_removed(payload.goal_id, GOALS_INDEX)

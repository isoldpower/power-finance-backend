from datetime import UTC

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import GoalUpdated

from data_read_core.shared.elasticsearch import (
    GOALS_INDEX,
    SEARCHABLE_REFRESH,
    get_elasticsearch,
)

from .._logger_shortcuts import log_goal_elastic_updated
from .._utilities import decode_payload


class UpdateGoalDocument(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, GoalUpdated)
        partial = {
            "id": payload.goal_id,
            "user_id": payload.user_id,
            "title": payload.new_title,
            "target": payload.target or "0",
            "url": payload.url or None,
            "finish_at": (
                payload.finish_at.ToDatetime(tzinfo=UTC).isoformat()
                if payload.HasField("finish_at")
                else None
            ),
            "updated_at": payload.updated_at.ToDatetime(tzinfo=UTC).isoformat(),
        }

        await get_elasticsearch().update(
            index=GOALS_INDEX,
            id=payload.goal_id,
            doc=partial,
            doc_as_upsert=True,
            refresh=SEARCHABLE_REFRESH,
        )
        log_goal_elastic_updated(payload.goal_id, GOALS_INDEX)

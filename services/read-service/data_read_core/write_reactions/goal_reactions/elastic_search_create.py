from datetime import UTC

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import GoalCreated

from data_read_core.shared.elasticsearch import (
    GOALS_INDEX,
    SEARCHABLE_REFRESH,
    get_elasticsearch,
)

from .._logger_shortcuts import log_goal_elastic_created
from .._utilities import decode_payload


class IndexGoalDocument(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, GoalCreated)
        document = {
            "id": payload.goal_id,
            "user_id": payload.user_id,
            "title": payload.title,
            "currency_code": payload.currency_code,
            "target": payload.target or "0",
            "progress": 0,
            "url": payload.url or None,
            "finish_at": (
                payload.finish_at.ToDatetime(tzinfo=UTC).isoformat()
                if payload.HasField("finish_at")
                else None
            ),
            "created_at": payload.created_at.ToDatetime(tzinfo=UTC).isoformat(),
            "updated_at": None,
            "deleted_at": None,
        }

        await get_elasticsearch().index(
            index=GOALS_INDEX,
            id=payload.goal_id,
            document=document,
            refresh=SEARCHABLE_REFRESH,
        )
        log_goal_elastic_created(payload.goal_id, GOALS_INDEX)

from datetime import UTC
from decimal import Decimal

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import GoalCreated

from data_read_core.shared.postgres_orm import GoalReadModel

from .._logger_shortcuts import log_goal_postgres_created
from .._utilities import decode_payload, handle_database_errors


class CreateGoalReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, GoalCreated)
        await handle_database_errors(
            self._create_goal,
            payload,
            resource_id=payload.goal_id,
        )

    async def _create_goal(self, payload: GoalCreated) -> GoalReadModel:
        created_goal = await GoalReadModel.objects.acreate(
            id=payload.goal_id,
            user_id=payload.user_id,
            title=payload.title,
            currency_code=payload.currency_code,
            target=Decimal(payload.target or "0"),
            progress=Decimal("0"),
            url=payload.url or None,
            finish_at=(
                payload.finish_at.ToDatetime(tzinfo=UTC) if payload.HasField("finish_at") else None
            ),
            created_at=payload.created_at.ToDatetime(tzinfo=UTC),
            updated_at=None,
            deleted_at=None,
        )

        log_goal_postgres_created(payload.goal_id)
        return created_goal

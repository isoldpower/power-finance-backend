from kafka_consumer_py import Effect, EventMessage
from kafka_messages import GoalUpdated

from data_read_core.shared.postgres_orm import MoneyContainers, TransactionReadModel

from .._logger_shortcuts import log_goal_transactions_renamed
from .._utilities import decode_payload, handle_database_errors


class RenameGoalInTransactions(Effect):
    """Carry a goal rename into the transactions that reference it."""

    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, GoalUpdated)
        await handle_database_errors(
            self._rename,
            payload,
            resource_id=payload.goal_id,
        )

    async def _rename(self, payload: GoalUpdated) -> None:
        if payload.previous_title == payload.new_title:
            return

        renamed = await TransactionReadModel.objects.filter(
            wallet_id=payload.goal_id,
            container_kind=MoneyContainers.GOAL,
        ).aupdate(wallet_name=payload.new_title)

        log_goal_transactions_renamed(payload.goal_id, renamed)

from kafka_messages import GoalUpdated

from data_read_core.shared.kafka_updates import Effect, EventMessage
from data_read_core.shared.postgres_orm import MoneyContainers, TransactionReadModel

from .._logger_shortcuts import log_goal_transactions_renamed
from .._utilities import decode_payload, handle_database_errors


class RenameGoalInTransactions(Effect):
    """Carry a goal rename into the transactions that reference it.

    Transaction rows denormalise the container's name so a listing needs no join.
    The kind filter matters: a wallet and a goal could in principle share an id, and
    without it a rename would reach across kinds.
    """

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

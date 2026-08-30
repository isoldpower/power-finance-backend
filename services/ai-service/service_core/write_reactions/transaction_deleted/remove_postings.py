from datetime import UTC, datetime
from uuid import UUID, uuid4

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import TransactionDeleted

from service_core.shared.logging import (
    debug_nothing_to_remove,
    log_balances_recomputed,
    log_postings_removed,
)
from service_core.shared.payloads import decode_payload

from .events import removal_events
from .exceptions import UnknownUserError
from .infrastructure import SqlAlchemyRemovalUnitOfWork
from .repositories import RemovalUnitOfWork, UnitOfWorkFactory


class RemovePostings(Effect):
    def __init__(
        self,
        unit_of_work: UnitOfWorkFactory = SqlAlchemyRemovalUnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionDeleted)
        transaction_id = UUID(payload.transaction_id)

        async with self._unit_of_work() as work:
            removed = await work.entries.remove_for_transaction(transaction_id)
            if not removed:
                debug_nothing_to_remove(str(transaction_id))
                return

            external_id = await _external_id(work, payload.user_id)

            now = datetime.now(UTC)
            dispatch_id = uuid4()

            changes = await work.accounts.recompute_balances(
                {posting.account_id for posting in removed},
                now,
            )

            await work.outbox.publish(
                removal_events(
                    removed=removed,
                    changes=changes,
                    dispatch_id=dispatch_id,
                    transaction_id=transaction_id,
                    user_id=payload.user_id,
                    user_external_id=external_id,
                    now=now,
                )
            )

        log_postings_removed(str(transaction_id))
        log_balances_recomputed(len(changes))


async def _external_id(work: RemovalUnitOfWork, user_id: int) -> str:
    external_id = await work.users.external_id_for(user_id)
    if external_id is None:
        raise UnknownUserError(user_id)

    return external_id

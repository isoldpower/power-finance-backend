from datetime import UTC, datetime
from uuid import UUID, uuid4

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import TransactionUpdated

from service_core.shared.logging import (
    debug_unknown_transaction,
    log_balances_recomputed,
    log_postings_dispatched,
)
from service_core.shared.payloads import decode_payload

from .dispatchers import DispatcherFactory
from .events import replacement_events
from .exceptions import UnknownUserError
from .infrastructure import SqlAlchemyDispatchUnitOfWork
from .repositories import DispatchUnitOfWork, UnitOfWorkFactory


class DispatchPostings(Effect):
    def __init__(
        self,
        build_dispatcher: DispatcherFactory,
        unit_of_work: UnitOfWorkFactory = SqlAlchemyDispatchUnitOfWork,
    ) -> None:
        self._build_dispatcher = build_dispatcher
        self._unit_of_work = unit_of_work

    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionUpdated)
        transaction_id = UUID(payload.transaction_id)

        async with self._unit_of_work() as work:
            transaction = await work.transactions.get(transaction_id)
            if transaction is None or transaction.deleted_at is not None:
                debug_unknown_transaction(str(transaction_id))
                return

            postings = await self._build_dispatcher(work.accounts).dispatch(transaction)
            external_id = await _external_id(work, transaction.user_id)

            now = datetime.now(UTC)
            dispatch_id = uuid4()

            touched = await work.entries.accounts_behind(transaction_id)
            touched.update(leg.account_id for leg in postings.legs)

            replaced = await work.entries.replace_for_transaction(
                transaction_id,
                transaction.user_id,
                postings.legs,
                now,
            )
            changes = await work.accounts.recompute_balances(touched, now)

            await work.outbox.publish(
                replacement_events(
                    removed=replaced.removed,
                    created=replaced.created,
                    changes=changes,
                    dispatch_id=dispatch_id,
                    transaction_id=transaction_id,
                    user_id=transaction.user_id,
                    user_external_id=external_id,
                    balanced=postings.balanced,
                    comment=postings.comment,
                    backend=postings.backend,
                    now=now,
                )
            )

        log_postings_dispatched(
            str(transaction_id),
            len(postings.legs),
            postings.backend,
        )
        log_balances_recomputed(len(changes))


async def _external_id(work: DispatchUnitOfWork, user_id: int) -> str:
    external_id = await work.users.external_id_for(user_id)
    if external_id is None:
        raise UnknownUserError(user_id)

    return external_id

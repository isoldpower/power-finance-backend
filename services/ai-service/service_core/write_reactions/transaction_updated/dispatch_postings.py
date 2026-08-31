from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import TransactionUpdated

from service_core.shared.exchange_rates import get_rate_service
from service_core.shared.logging import (
    debug_unknown_transaction,
    log_balances_recomputed,
    log_postings_dispatched,
)
from service_core.shared.payloads import decode_payload

from .booking import book_legs
from .contracts import (
    BalanceChange,
    DispatchedPostings,
    ExchangeRates,
    ReplacedPostings,
    TransactionFacts,
)
from .dispatchers import DispatcherFactory
from .events import replacement_events
from .exceptions import UnknownUserError
from .infrastructure import SqlAlchemyDispatchUnitOfWork
from .repositories import DispatchUnitOfWork, UnitOfWorkFactory


@dataclass(frozen=True, slots=True)
class _Dispatched:
    postings: DispatchedPostings
    rebalanced: Sequence[BalanceChange]


class DispatchPostings(Effect):
    def __init__(
        self,
        build_dispatcher: DispatcherFactory,
        unit_of_work: UnitOfWorkFactory = SqlAlchemyDispatchUnitOfWork,
        exchange_rates: ExchangeRates | None = None,
    ) -> None:
        self._build_dispatcher = build_dispatcher
        self._unit_of_work = unit_of_work
        self._exchange_rates = exchange_rates

    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionUpdated)
        transaction_id = UUID(payload.transaction_id)

        dispatched = await self._dispatch(transaction_id)
        if dispatched is None:
            return

        log_postings_dispatched(
            str(transaction_id),
            len(dispatched.postings.legs),
            dispatched.postings.backend,
        )
        log_balances_recomputed(len(dispatched.rebalanced))

    async def _dispatch(self, transaction_id: UUID) -> _Dispatched | None:
        async with self._unit_of_work() as work:
            transaction = await work.transactions.get(transaction_id)
            if transaction is None or transaction.deleted_at is not None:
                debug_unknown_transaction(str(transaction_id))
                return None

            postings = await self._build_dispatcher(work.accounts).dispatch(transaction)
            external_id = await _external_id(work, transaction.user_id)
            now = datetime.now(UTC)

            replaced, touched = await self._replace_postings(
                work,
                transaction,
                transaction_id,
                postings,
                now,
            )
            rebalanced = await work.accounts.recompute_balances(touched, now)

            await self._publish(
                work,
                transaction=transaction,
                transaction_id=transaction_id,
                external_id=external_id,
                postings=postings,
                replaced=replaced,
                rebalanced=rebalanced,
                now=now,
            )

            return _Dispatched(postings=postings, rebalanced=rebalanced)

    async def _replace_postings(
        self,
        work: DispatchUnitOfWork,
        transaction: TransactionFacts,
        transaction_id: UUID,
        postings: DispatchedPostings,
        now: datetime,
    ) -> tuple[ReplacedPostings, set[UUID]]:
        touched = await work.entries.accounts_behind(transaction_id)
        touched.update(leg.account_id for leg in postings.legs)

        booked = await book_legs(
            postings.legs,
            self._rates(),
            transaction_currency=transaction.currency_code,
        )
        replaced = await work.entries.replace_for_transaction(
            transaction_id,
            transaction.user_id,
            booked,
            now,
        )

        return replaced, touched

    async def _publish(
        self,
        work: DispatchUnitOfWork,
        *,
        transaction: TransactionFacts,
        transaction_id: UUID,
        external_id: str,
        postings: DispatchedPostings,
        replaced: ReplacedPostings,
        rebalanced: Sequence[BalanceChange],
        now: datetime,
    ) -> None:
        await work.outbox.publish(
            replacement_events(
                removed=replaced.removed,
                created=replaced.created,
                changes=rebalanced,
                dispatch_id=uuid4(),
                transaction_id=transaction_id,
                user_id=transaction.user_id,
                user_external_id=external_id,
                balanced=postings.balanced,
                comment=postings.comment,
                backend=postings.backend,
                now=now,
            )
        )

    def _rates(self) -> ExchangeRates:
        if self._exchange_rates is None:
            self._exchange_rates = get_rate_service()

        return self._exchange_rates


async def _external_id(work: DispatchUnitOfWork, user_id: int) -> str:
    external_id = await work.users.external_id_for(user_id)
    if external_id is None:
        raise UnknownUserError(user_id)

    return external_id

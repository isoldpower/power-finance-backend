from datetime import UTC
from uuid import UUID

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import TransactionUpdated

from service_core.shared.logging import log_transaction_amount_updated
from service_core.shared.payloads import decode_payload, parse_money

from .infrastructure import SqlAlchemyDispatchUnitOfWork
from .repositories import UnitOfWorkFactory


class UpdateProjectedTransactionAmount(Effect):
    """Applies a new amount to an already-projected transaction."""

    def __init__(self, unit_of_work: UnitOfWorkFactory = SqlAlchemyDispatchUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionUpdated)

        async with self._unit_of_work() as work:
            await work.transactions.update_amount(
                UUID(payload.transaction_id),
                parse_money(payload.new_amount),
                payload.updated_at.ToDatetime(tzinfo=UTC),
                event.outbox_seq or 0,
            )

        log_transaction_amount_updated(payload.transaction_id)

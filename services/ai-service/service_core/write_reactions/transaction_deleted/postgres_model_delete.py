from datetime import UTC
from uuid import UUID

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import TransactionDeleted

from service_core.shared.logging import log_transaction_soft_deleted
from service_core.shared.payloads import decode_payload

from .infrastructure import SqlAlchemyRemovalUnitOfWork
from .repositories import UnitOfWorkFactory


class SoftDeleteProjectedTransaction(Effect):
    """Marks a transaction deleted rather than removing the row."""

    def __init__(self, unit_of_work: UnitOfWorkFactory = SqlAlchemyRemovalUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionDeleted)

        async with self._unit_of_work() as work:
            await work.transactions.soft_delete(
                UUID(payload.transaction_id),
                payload.deleted_at.ToDatetime(tzinfo=UTC),
                event.outbox_seq or 0,
            )

        log_transaction_soft_deleted(payload.transaction_id)

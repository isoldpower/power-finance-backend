from datetime import UTC
from uuid import UUID

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import TransactionCreated

from service_core.shared.logging import log_transaction_projected
from service_core.shared.payloads import decode_payload, parse_money

from .contracts import TransactionFacts
from .infrastructure import SqlAlchemyDispatchUnitOfWork
from .repositories import UnitOfWorkFactory


class ProjectTransaction(Effect):
    def __init__(
        self,
        unit_of_work: UnitOfWorkFactory = SqlAlchemyDispatchUnitOfWork,
    ) -> None:
        self._unit_of_work = unit_of_work

    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionCreated)
        facts = TransactionFacts(
            id=UUID(payload.transaction_id),
            user_id=payload.user_id,
            container_id=UUID(payload.wallet_id),
            container_kind=payload.container_kind,
            amount=parse_money(payload.amount),
            created_at=payload.created_at.ToDatetime(tzinfo=UTC),
            currency_code=payload.currency_code,
            name=payload.name,
            category=payload.category,
            evidence_url=payload.evidence_url,
            origin=payload.origin,
            chain_id=payload.chain_id,
        )

        async with self._unit_of_work() as work:
            await work.transactions.project(facts, event.outbox_seq or 0)

        log_transaction_projected(payload.transaction_id)

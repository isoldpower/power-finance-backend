from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from service_core.shared.db_connection import ProjectedTransaction

from ..contracts import TransactionFacts
from ..repositories import ProjectedTransactionRepository
from ._facts import facts_of

_REPROJECTED_FIELDS = ("amount", "name", "category", "evidence_url")


class SqlAlchemyProjectedTransactionRepository(ProjectedTransactionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, transaction_id: UUID) -> TransactionFacts | None:
        transaction_row = await self._session.get(
            ProjectedTransaction,
            transaction_id,
        )

        return facts_of(transaction_row) if transaction_row is not None else None

    async def project(self, facts: TransactionFacts, applied_seq: int) -> None:
        values = {
            "id": facts.id,
            "user_id": facts.user_id,
            "container_id": facts.container_id,
            "container_kind": facts.container_kind,
            "amount": facts.amount,
            "name": facts.name,
            "category": facts.category,
            "evidence_url": facts.evidence_url,
            "origin": facts.origin,
            "chain_id": facts.chain_id,
            "created_at": facts.created_at,
            "applied_seq": applied_seq,
        }

        await self._session.execute(
            insert(ProjectedTransaction)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[ProjectedTransaction.id],
                set_={field: values[field] for field in _REPROJECTED_FIELDS}
                | {"applied_seq": applied_seq},
                where=ProjectedTransaction.applied_seq < applied_seq,
            )
        )

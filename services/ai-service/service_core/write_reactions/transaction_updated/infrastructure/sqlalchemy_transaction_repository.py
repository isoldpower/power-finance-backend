from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from service_core.shared.db_connection import ProjectedTransaction

from ..contracts import TransactionFacts
from ..repositories import ProjectedTransactionRepository
from ._facts import facts_of


class SqlAlchemyProjectedTransactionRepository(ProjectedTransactionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, transaction_id: UUID) -> TransactionFacts | None:
        transaction_row = await self._session.get(
            ProjectedTransaction,
            transaction_id,
        )

        return facts_of(transaction_row) if transaction_row is not None else None

    async def update_amount(
        self,
        transaction_id: UUID,
        amount: Decimal,
        updated_at: datetime,
        applied_seq: int,
    ) -> None:
        await self._session.execute(
            update(ProjectedTransaction)
            .where(
                ProjectedTransaction.id == transaction_id,
                ProjectedTransaction.applied_seq < applied_seq,
            )
            .values(
                applied_seq=applied_seq,
                amount=amount,
                updated_at=updated_at,
            )
        )

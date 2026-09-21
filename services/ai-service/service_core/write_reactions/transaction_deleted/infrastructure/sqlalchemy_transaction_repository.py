from datetime import datetime
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from service_core.shared.db_connection import ProjectedTransaction

from ..repositories import ProjectedTransactionRepository


class SqlAlchemyProjectedTransactionRepository(ProjectedTransactionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def soft_delete(
        self,
        transaction_id: UUID,
        deleted_at: datetime,
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
                deleted_at=deleted_at,
            )
        )

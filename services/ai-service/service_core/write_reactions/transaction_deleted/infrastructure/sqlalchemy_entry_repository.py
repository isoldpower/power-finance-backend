from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from service_core.shared.db_connection import EntryModel

from ..contracts import RemovedPosting
from ..repositories import EntryRepository


class SqlAlchemyEntryRepository(EntryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def remove_for_transaction(self, transaction_id: UUID) -> list[RemovedPosting]:
        gone = await self._session.execute(
            delete(EntryModel)
            .where(EntryModel.transaction_id == transaction_id)
            .returning(EntryModel.id, EntryModel.account_id)
        )

        return [
            RemovedPosting(posting_id=posting_id, account_id=account_id)
            for posting_id, account_id in gone.all()
        ]

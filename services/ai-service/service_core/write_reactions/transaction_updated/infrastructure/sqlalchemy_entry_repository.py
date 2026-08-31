from collections.abc import Sequence
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from service_core.shared.db_connection import EntryModel

from ..contracts import BookedLeg, RemovedPosting, ReplacedPostings, StoredPosting
from ..repositories import EntryRepository


class SqlAlchemyEntryRepository(EntryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def accounts_behind(self, transaction_id: UUID) -> set[UUID]:
        rows = await self._session.execute(
            select(EntryModel.account_id)
            .where(EntryModel.transaction_id == transaction_id)
            .distinct()
        )

        return set(rows.scalars())

    async def replace_for_transaction(
        self,
        transaction_id: UUID,
        user_id: int,
        legs: Sequence[BookedLeg],
        now: datetime,
    ) -> ReplacedPostings:
        removed_postings = await self._remove(transaction_id)
        created_postings = [StoredPosting(posting_id=uuid4(), leg=booked.leg) for booked in legs]

        for posting, booked in zip(created_postings, legs, strict=True):
            posting_left = posting.leg
            self._session.add(
                EntryModel(
                    id=posting.posting_id,
                    user_id=user_id,
                    account_id=posting_left.account_id,
                    transaction_id=transaction_id,
                    title=posting_left.title,
                    icon=posting_left.icon,
                    debit=posting_left.debit,
                    amount=posting_left.amount,
                    currency_code=posting_left.currency_code,
                    book_amount=booked.book_amount,
                    book_currency=booked.book_currency,
                    conversion_rate=booked.conversion_rate,
                    position=posting_left.position,
                    created_at=now,
                )
            )

        await self._session.flush()
        return ReplacedPostings(
            removed=tuple(removed_postings),
            created=tuple(created_postings),
        )

    async def _remove(self, transaction_id: UUID) -> list[RemovedPosting]:
        gone = await self._session.execute(
            delete(EntryModel)
            .where(EntryModel.transaction_id == transaction_id)
            .returning(EntryModel.id, EntryModel.account_id)
        )

        return [
            RemovedPosting(posting_id=posting_id, account_id=account_id)
            for posting_id, account_id in gone.all()
        ]

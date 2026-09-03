from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from service_core.shared.db_connection import ProjectedTransaction, UserModel

from ..contracts import ActivitySource, ConversationActivity

EMPTY = ConversationActivity(
    spend_currency="",
    spend_this_month=Decimal(0),
    spend_last_month=Decimal(0),
    uncategorised=0,
    recorded_this_month=0,
)


class SqlAlchemyActivitySource(ActivitySource):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def read(self, external_id: str) -> ConversationActivity:
        async with self._session_factory() as session:
            user_id = await session.scalar(
                select(UserModel.user_id).where(UserModel.external_id == external_id)
            )
            if user_id is None:
                return EMPTY

            this_month, last_month = month_bounds(datetime.now(UTC))
            currency = await self._dominant_currency(session, user_id, last_month)

            return ConversationActivity(
                spend_currency=currency,
                spend_this_month=await self._spend(
                    session,
                    user_id,
                    currency,
                    this_month,
                    None,
                ),
                spend_last_month=await self._spend(
                    session,
                    user_id,
                    currency,
                    last_month,
                    this_month,
                ),
                uncategorised=await self._uncategorised(session, user_id),
                recorded_this_month=await self._recorded(session, user_id, this_month),
            )

    async def _dominant_currency(self, session, user_id: int, since: datetime) -> str:
        return (
            await session.scalar(
                select(ProjectedTransaction.currency_code)
                .where(*_live(user_id), ProjectedTransaction.created_at >= since)
                .group_by(ProjectedTransaction.currency_code)
                .order_by(func.count().desc(), ProjectedTransaction.currency_code)
                .limit(1)
            )
            or ""
        )

    async def _spend(
        self,
        session,
        user_id: int,
        currency: str,
        since: datetime,
        until: datetime | None,
    ) -> Decimal:
        if not currency:
            return Decimal(0)

        conditions = [
            *_live(user_id),
            ProjectedTransaction.currency_code == currency,
            ProjectedTransaction.amount < 0,
            ProjectedTransaction.created_at >= since,
        ]
        if until is not None:
            conditions.append(ProjectedTransaction.created_at < until)

        total = await session.scalar(
            select(func.coalesce(func.sum(ProjectedTransaction.amount), 0)).where(*conditions)
        )

        return abs(Decimal(total or 0))

    async def _uncategorised(self, session, user_id: int) -> int:
        total = await session.scalar(
            select(func.count()).where(*_live(user_id), ProjectedTransaction.category == "")
        )

        return int(total or 0)

    async def _recorded(self, session, user_id: int, since: datetime) -> int:
        total = await session.scalar(
            select(func.count()).where(*_live(user_id), ProjectedTransaction.created_at >= since)
        )

        return int(total or 0)


def month_bounds(now: datetime) -> tuple[datetime, datetime]:
    this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month = (
        this_month.replace(year=this_month.year - 1, month=12)
        if this_month.month == 1
        else this_month.replace(month=this_month.month - 1)
    )

    return this_month, last_month


def _live(user_id: int) -> tuple:
    return (
        ProjectedTransaction.user_id == user_id,
        ProjectedTransaction.deleted_at.is_(None),
    )

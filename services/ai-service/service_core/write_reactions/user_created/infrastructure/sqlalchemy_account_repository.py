from collections.abc import Sequence
from datetime import datetime
from uuid import uuid4

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from service_core.shared.db_connection import AccountModel

from ..contracts import BOOK_CURRENCY, AccountRecord, AccountSpec
from ..repositories import AccountRepository


class SqlAlchemyAccountRepository(AccountRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ensure(
        self,
        user_id: int,
        accounts: Sequence[AccountSpec],
        now: datetime,
    ) -> list[AccountRecord]:
        if not accounts:
            return []

        created = await self._session.execute(
            insert(AccountModel)
            .values(
                [
                    {
                        "id": uuid4(),
                        "user_id": user_id,
                        "group": spec.group,
                        "name": spec.name,
                        "balance": 0,
                        "currency_code": BOOK_CURRENCY,
                        "created_at": now,
                    }
                    for spec in accounts
                ]
            )
            .on_conflict_do_nothing(constraint="ai_accounts_identity")
            .returning(
                AccountModel.id,
                AccountModel.group,
                AccountModel.name,
                AccountModel.balance,
                AccountModel.currency_code,
                AccountModel.created_at,
            )
        )

        return [
            AccountRecord(
                account_id=account_id,
                group=group,
                name=name,
                balance=balance,
                currency_code=currency_code,
                created_at=created_at,
            )
            for account_id, group, name, balance, currency_code, created_at in created.all()
        ]

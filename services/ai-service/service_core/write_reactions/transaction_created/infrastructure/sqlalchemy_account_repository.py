from collections.abc import Collection, Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession

from service_core.shared.db_connection import AccountModel, EntryModel

from ..contracts import AccountSpec, BalanceChange
from ..exceptions import UnknownAccountsError
from ..repositories import AccountRepository
from ._signed_amount import signed_amount


class SqlAlchemyAccountRepository(AccountRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def resolve(
        self,
        user_id: int,
        accounts: Sequence[AccountSpec],
    ) -> list[UUID]:
        if not accounts:
            return []

        accounts_rows = await self._session.execute(
            select(AccountModel.group, AccountModel.name, AccountModel.id).where(
                AccountModel.user_id == user_id,
                tuple_(AccountModel.group, AccountModel.name).in_(
                    [(spec.group, spec.name) for spec in accounts]
                ),
            )
        )
        accounts_dict = {
            (group, name): account_id for group, name, account_id in accounts_rows.all()
        }
        missing_accounts = [
            account for account in accounts if (account.group, account.name) not in accounts_dict
        ]

        if missing_accounts:
            raise UnknownAccountsError(user_id, missing_accounts)

        return [accounts_dict[(account.group, account.name)] for account in accounts]

    async def recompute_balances(
        self,
        account_ids: Collection[UUID],
        now: datetime,
    ) -> list[BalanceChange]:
        if not account_ids:
            return []

        balance_of_the_account = (
            select(func.coalesce(func.sum(signed_amount()), 0))
            .where(EntryModel.account_id == AccountModel.id)
            .correlate(AccountModel)
            .scalar_subquery()
        )
        balances_before = (
            select(
                AccountModel.id.label("id"),
                AccountModel.balance.label("previous"),
            )
            .where(AccountModel.id.in_(set(account_ids)))
            .cte("balances_before")
        )

        moved = await self._session.execute(
            update(AccountModel)
            .where(AccountModel.id == balances_before.c.id)
            .where(AccountModel.balance.is_distinct_from(balance_of_the_account))
            .values(balance=balance_of_the_account, updated_at=now)
            .returning(
                AccountModel.id,
                AccountModel.group,
                AccountModel.name,
                balances_before.c.previous,
                AccountModel.balance,
            )
        )

        return [
            BalanceChange(
                account_id=account_id,
                group=group,
                name=name,
                previous=previous,
                current=current,
            )
            for account_id, group, name, previous, current in moved.all()
        ]

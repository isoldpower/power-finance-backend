"""The account repository against a real database: seeding, and reading back."""

import pytest
from kafka_consumer_py.fakes import make_event
from sqlalchemy import select

from service_core.shared.db_connection import AccountModel, session_scope
from service_core.write_reactions import (
    transaction_created,
    user_created,
)

from .fakes import USER_ID, make_user_synced
from .template import (
    CREATED_TEMPLATE_ACCOUNTS,
    SEED_TEMPLATE_ACCOUNTS,
)

OTHER_USER_ID = USER_ID + 1


async def _resolve(user_id: int, specifications):
    async with transaction_created.SqlAlchemyDispatchUnitOfWork() as work:
        return await work.accounts.resolve(user_id, specifications)


async def _seed(user_id: int = USER_ID) -> None:
    await user_created.SeedTemplateAccounts(SEED_TEMPLATE_ACCOUNTS).apply(
        make_event(make_user_synced(user_id=user_id))
    )


async def test_user_synced_seeds_the_template_accounts():
    await _seed()

    async with session_scope() as session:
        rows = await session.execute(
            select(AccountModel.group, AccountModel.name, AccountModel.balance).where(
                AccountModel.user_id == USER_ID
            )
        )
        assert sorted(rows.all()) == sorted(
            (account.specification.group, account.specification.name, 0)
            for account in CREATED_TEMPLATE_ACCOUNTS
        )


async def test_seeding_the_same_user_twice_does_not_duplicate_the_accounts():
    """A re-sync is normal, and the second one must not mint a parallel chart."""

    await _seed()
    await _seed()

    async with session_scope() as session:
        count = await session.execute(select(AccountModel).where(AccountModel.user_id == USER_ID))
        assert len(count.scalars().all()) == len(CREATED_TEMPLATE_ACCOUNTS)


async def test_the_repository_returns_ids_in_the_order_asked_for():
    await _seed()
    specs = [account.specification for account in CREATED_TEMPLATE_ACCOUNTS]

    ids = await _resolve(USER_ID, specs)

    async with session_scope() as session:
        rows = await session.execute(
            select(AccountModel.id, AccountModel.group, AccountModel.name).where(
                AccountModel.user_id == USER_ID
            )
        )
        by_identity = {(group, name): account_id for account_id, group, name in rows.all()}

    assert ids == [by_identity[(spec.group, spec.name)] for spec in specs]


async def test_another_user_s_accounts_do_not_resolve():
    """The seeded rows are per-user, so a dispatch for a user nobody synced must
    not quietly post against someone else's chart."""

    await _seed(OTHER_USER_ID)

    with pytest.raises(transaction_created.UnknownAccountsError):
        await _resolve(USER_ID, [account.specification for account in CREATED_TEMPLATE_ACCOUNTS])


async def test_a_missing_account_is_named_in_the_error():
    await _seed()
    unknown = transaction_created.AccountSpec(group="equity", name="nowhere")

    with pytest.raises(transaction_created.UnknownAccountsError) as raised:
        await _resolve(USER_ID, [unknown])

    assert raised.value.missing == (unknown,)
    assert "equity/nowhere" in str(raised.value)


async def test_resolving_nothing_asks_the_database_nothing():
    assert await _resolve(USER_ID, []) == []

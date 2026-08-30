"""The unit of work: one transaction, three repositories.

Its whole reason for existing is that a projection and the legs dispatched from
it either both land or neither does, so what is tested here is the boundary
rather than any one repository's SQL.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from kafka_consumer_py.fakes import make_event
from sqlalchemy import func, select

from service_core.shared.db_connection import (
    AccountModel,
    EntryModel,
    ProjectedTransaction,
    session_scope,
)
from service_core.write_reactions import (
    transaction_created,
    user_created,
)

from .fakes import (
    TRANSACTION_ID,
    USER_ID,
    make_transaction_created,
    make_user_synced,
)
from .template import (
    CREATED_TEMPLATE_ACCOUNTS,
    SEED_TEMPLATE_ACCOUNTS,
    build_created_dispatcher,
)

OTHER_TRANSACTION_ID = UUID("44444444-4444-4444-8444-444444444444")


def _facts(transaction_id: UUID = OTHER_TRANSACTION_ID) -> transaction_created.TransactionFacts:
    return transaction_created.TransactionFacts(
        id=transaction_id,
        user_id=USER_ID,
        container_id=UUID("22222222-2222-4222-8222-222222222222"),
        container_kind="wallet",
        amount=Decimal("10.00"),
        created_at=datetime(2026, 8, 26, 9, 0, tzinfo=UTC),
    )


async def _count(model) -> int:
    async with session_scope() as session:
        return (await session.execute(select(func.count()).select_from(model))).scalar_one()


async def test_work_done_inside_is_committed_on_a_clean_exit():
    async with transaction_created.SqlAlchemyDispatchUnitOfWork() as work:
        await work.transactions.project(_facts(), 1)

    assert await _count(ProjectedTransaction) == 1


async def test_an_exception_rolls_the_whole_unit_back():
    """Not just the failing statement — everything the unit of work had done."""

    with pytest.raises(RuntimeError):
        async with transaction_created.SqlAlchemyDispatchUnitOfWork() as work:
            await work.transactions.project(_facts(), 1)
            raise RuntimeError("something later went wrong")

    assert await _count(ProjectedTransaction) == 0


async def test_the_repositories_share_one_transaction():
    """A write through one repository is visible to another before any commit,
    which is what lets a dispatch read the projection it just made."""

    async with transaction_created.SqlAlchemyDispatchUnitOfWork() as work:
        await work.transactions.project(_facts(), 1)

        assert await work.transactions.get(OTHER_TRANSACTION_ID) is not None


async def test_repositories_are_unreachable_before_the_unit_is_entered():
    work = transaction_created.SqlAlchemyDispatchUnitOfWork()

    with pytest.raises(RuntimeError, match="not been entered"):
        _ = work.accounts


async def test_repositories_are_released_again_on_exit():
    work = transaction_created.SqlAlchemyDispatchUnitOfWork()
    async with work:
        pass

    with pytest.raises(RuntimeError, match="not been entered"):
        _ = work.entries


class _FailingBalances(transaction_created.AccountRepository):
    """A real repository with its last step sabotaged."""

    def __init__(self, inner: transaction_created.AccountRepository) -> None:
        self._inner = inner

    async def ensure(self, user_id, accounts, now) -> None:
        await self._inner.ensure(user_id, accounts, now)

    async def resolve(self, user_id, accounts):
        return await self._inner.resolve(user_id, accounts)

    async def recompute_balances(self, account_ids, now) -> None:
        raise RuntimeError("balances blew up")


class _SabotagedUnitOfWork(transaction_created.DispatchUnitOfWork):
    """A real unit of work whose balance recomputation fails, so the failure
    lands after the legs have been written and flushed."""

    def __init__(self) -> None:
        self._inner = transaction_created.SqlAlchemyDispatchUnitOfWork()

    async def __aenter__(self) -> "_SabotagedUnitOfWork":
        await self._inner.__aenter__()
        return self

    async def __aexit__(self, exception_type, exception, traceback) -> None:
        await self._inner.__aexit__(exception_type, exception, traceback)

    @property
    def accounts(self) -> transaction_created.AccountRepository:
        return _FailingBalances(self._inner.accounts)

    @property
    def entries(self):
        return self._inner.entries

    @property
    def transactions(self):
        return self._inner.transactions

    @property
    def users(self):
        return self._inner.users

    @property
    def outbox(self):
        return self._inner.outbox


async def test_legs_already_flushed_are_rolled_back_when_a_later_step_fails():
    """The case the boundary exists for. `replace_for_transaction` flushes, so
    the rows are in the database by the time the recomputation raises; without
    one transaction around both they would survive with stale balances."""

    await user_created.SeedTemplateAccounts(SEED_TEMPLATE_ACCOUNTS).apply(
        make_event(make_user_synced())
    )
    await transaction_created.ProjectTransaction().apply(
        make_event(make_transaction_created(), outbox_seq=1)
    )

    with pytest.raises(RuntimeError, match="balances blew up"):
        await transaction_created.DispatchPostings(
            build_created_dispatcher,
            _SabotagedUnitOfWork,
        ).apply(make_event(make_transaction_created(), outbox_seq=1))

    assert await _count(EntryModel) == 0
    assert await _count(AccountModel) == len(CREATED_TEMPLATE_ACCOUNTS)


async def test_a_dispatcher_that_raises_writes_nothing():
    await user_created.SeedTemplateAccounts(SEED_TEMPLATE_ACCOUNTS).apply(
        make_event(make_user_synced())
    )
    await transaction_created.ProjectTransaction().apply(
        make_event(make_transaction_created(), outbox_seq=1)
    )

    def _explode(_accounts):
        raise transaction_created.UnknownAccountsError(
            USER_ID, [CREATED_TEMPLATE_ACCOUNTS[0].specification]
        )

    with pytest.raises(transaction_created.UnknownAccountsError):
        await transaction_created.DispatchPostings(_explode).apply(
            make_event(make_transaction_created(), outbox_seq=1)
        )

    assert await _count(EntryModel) == 0


async def test_a_dispatch_that_succeeds_still_commits():
    await user_created.SeedTemplateAccounts(SEED_TEMPLATE_ACCOUNTS).apply(
        make_event(make_user_synced())
    )
    await transaction_created.ProjectTransaction().apply(
        make_event(make_transaction_created(), outbox_seq=1)
    )

    await transaction_created.DispatchPostings(build_created_dispatcher).apply(
        make_event(make_transaction_created(), outbox_seq=1)
    )

    assert await _count(EntryModel) == len(CREATED_TEMPLATE_ACCOUNTS)
    async with session_scope() as session:
        projected = await session.get(ProjectedTransaction, TRANSACTION_ID)
        assert projected is not None

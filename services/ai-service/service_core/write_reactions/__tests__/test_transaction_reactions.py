"""The projection and dispatch effects, against a real database.

Every assertion here is about something the database decides: the upsert arm,
the `applied_seq` guard, the account identity constraint, and what survives a
delete.
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
    transaction_deleted,
    transaction_updated,
    user_created,
)

from ..transaction_created.__tests__.fakes import FixedRates, SingleLegDispatcher
from .fakes import (
    TRANSACTION_ID,
    USER_ID,
    make_transaction_created,
    make_transaction_deleted,
    make_transaction_updated,
    make_user_synced,
)
from .template import (
    CREATED_TEMPLATE_ACCOUNTS,
    SEED_TEMPLATE_ACCOUNTS,
    build_created_dispatcher,
    build_updated_dispatcher,
)


async def _load_transaction() -> ProjectedTransaction | None:
    async with session_scope() as session:
        return await session.get(ProjectedTransaction, TRANSACTION_ID)


async def _load_entries() -> list[EntryModel]:
    async with session_scope() as session:
        rows = await session.execute(select(EntryModel).order_by(EntryModel.position))
        return list(rows.scalars())


async def _count(model) -> int:
    async with session_scope() as session:
        return (await session.execute(select(func.count()).select_from(model))).scalar_one()


async def _project(**kwargs) -> None:
    await transaction_created.ProjectTransaction().apply(
        make_event(make_transaction_created(**kwargs), outbox_seq=1)
    )


async def _seed_accounts(user_id: int = USER_ID) -> None:
    """A dispatch reads the chart of accounts and never extends it, so every
    dispatching test needs the user's accounts to exist first."""

    await user_created.SeedTemplateAccounts(SEED_TEMPLATE_ACCOUNTS).apply(
        make_event(make_user_synced(user_id=user_id))
    )


async def _balances() -> dict[tuple[str, str], Decimal]:
    async with session_scope() as session:
        rows = await session.execute(
            select(AccountModel.group, AccountModel.name, AccountModel.balance)
        )
        return {(group, name): balance for group, name, balance in rows.all()}


def _template_key(position: int) -> tuple[str, str]:
    specification = CREATED_TEMPLATE_ACCOUNTS[position].specification
    return specification.group, specification.name


async def _dispatch_created(
    build_dispatcher=build_created_dispatcher,
    rates=None,
) -> None:
    await transaction_created.DispatchPostings(
        build_dispatcher,
        exchange_rates=rates or FixedRates(),
    ).apply(make_event(make_transaction_created(), outbox_seq=1))


async def test_a_created_transaction_is_copied_into_the_local_tables():
    await _project()

    transaction = await _load_transaction()

    assert transaction is not None
    assert transaction.user_id == USER_ID
    assert transaction.amount == Decimal("125.00")
    assert transaction.name == "Groceries"
    assert transaction.currency_code == "EUR"
    assert transaction.created_at == datetime(2026, 8, 25, 12, 0, tzinfo=UTC)


async def test_projecting_the_same_event_twice_leaves_one_row():
    """Redelivery is normal. An insert would fail the message and send a
    perfectly good transaction to the retry topic."""

    await _project()
    await _project()

    assert await _count(ProjectedTransaction) == 1


async def test_a_stale_event_does_not_overwrite_a_newer_projection():
    await transaction_created.ProjectTransaction().apply(
        make_event(make_transaction_created(amount="125.00"), outbox_seq=5)
    )
    await transaction_created.ProjectTransaction().apply(
        make_event(make_transaction_created(amount="1.00", name="stale"), outbox_seq=2)
    )

    transaction = await _load_transaction()

    assert transaction is not None
    assert transaction.amount == Decimal("125.00")
    assert transaction.name == "Groceries"


async def test_dispatch_writes_one_entry_per_leg():
    await _seed_accounts()
    await _project()

    await _dispatch_created()

    entries = await _load_entries()
    assert [(entry.debit, entry.amount) for entry in entries] == [
        (True, Decimal("125.00")),
        (False, Decimal("125.00")),
    ]


async def test_dispatch_posts_against_the_seeded_accounts_rather_than_minting_new_ones():
    await _seed_accounts()
    await _project()

    await _dispatch_created()

    assert await _count(AccountModel) == len(CREATED_TEMPLATE_ACCOUNTS)
    async with session_scope() as session:
        rows = await session.execute(select(EntryModel.account_id).distinct())
        entry_accounts = set(rows.scalars())
        rows = await session.execute(select(AccountModel.id))
        assert entry_accounts == set(rows.scalars())


async def test_a_dispatch_for_an_unseeded_user_fails_rather_than_inventing_accounts():
    """The accepted cost of seeding on `UserSynced`: a transaction that overtakes
    its owner's sync retries instead of quietly minting a chart of accounts."""

    await _project()

    with pytest.raises(transaction_created.UnknownAccountsError):
        await _dispatch_created()

    assert await _count(EntryModel) == 0


async def test_balances_follow_each_account_s_normal_side():
    """The template debits a liability and credits an asset, and each of those is
    the lowering side for its group, so both balances go negative. Nonsense as
    bookkeeping, but it still satisfies assets = liabilities + equity, and the
    raising direction is covered by the single-leg case below."""

    await _seed_accounts()
    await _project()

    await _dispatch_created()

    balances = await _balances()
    assert balances[_template_key(0)] == Decimal("-125.00")
    assert balances[_template_key(1)] == Decimal("-125.00")


async def test_balances_accumulate_across_transactions():
    await _seed_accounts()
    await _project()
    await _dispatch_created()

    second = UUID("33333333-3333-4333-8333-333333333333")
    await transaction_created.ProjectTransaction().apply(
        make_event(make_transaction_created(transaction_id=second, amount="75.00"), outbox_seq=2)
    )
    await transaction_created.DispatchPostings(
        build_created_dispatcher, exchange_rates=FixedRates()
    ).apply(
        make_event(make_transaction_created(transaction_id=second, amount="75.00"), outbox_seq=2)
    )

    assert (await _balances())[_template_key(0)] == Decimal("-200.00")


async def test_dispatching_twice_does_not_count_the_legs_twice():
    """Redelivery is normal. Balances are recomputed from the entries for exactly
    this reason — an increment would have to remember what it already counted."""

    await _seed_accounts()
    await _project()

    await _dispatch_created()
    await _dispatch_created()

    assert await _count(EntryModel) == len(CREATED_TEMPLATE_ACCOUNTS)
    assert (await _balances())[_template_key(0)] == Decimal("-125.00")


async def test_dispatch_replaces_the_previous_legs_rather_than_adding_to_them():
    await _seed_accounts()
    await _project()
    await _dispatch_created()

    async with session_scope() as session:
        spike_account = (
            await session.execute(select(AccountModel.id).where(AccountModel.group == "assets"))
        ).scalar_one()

    await _dispatch_created(lambda _accounts: SingleLegDispatcher(spike_account))

    entries = await _load_entries()
    assert len(entries) == 1
    assert entries[0].title == "spike"


async def test_an_account_a_dispatch_walked_away_from_is_re_balanced_too():
    """The accounts read before the delete matter as much as the ones written
    after it, or a moved leg leaves its old account permanently wrong."""

    await _seed_accounts()
    await _project()
    await _dispatch_created()

    async with session_scope() as session:
        assets_account = (
            await session.execute(select(AccountModel.id).where(AccountModel.group == "assets"))
        ).scalar_one()

    await _dispatch_created(lambda _accounts: SingleLegDispatcher(assets_account))

    balances = await _balances()
    assert balances[_template_key(0)] == Decimal("0.00")
    assert balances[_template_key(1)] == Decimal("1.00")


async def test_dispatch_skips_a_transaction_it_has_never_seen():
    """The projection and the dispatch share a group, so this only happens on a
    dispatch for an event whose create never arrived. Nothing to derive from."""

    await _seed_accounts()

    await _dispatch_created()

    assert await _count(EntryModel) == 0


async def test_an_updated_amount_reaches_the_projection():
    await _project()

    await transaction_updated.UpdateProjectedTransactionAmount().apply(
        make_event(make_transaction_updated(new_amount="200.00"), outbox_seq=2)
    )

    transaction = await _load_transaction()
    assert transaction is not None
    assert transaction.amount == Decimal("200.00")
    assert transaction.updated_at == datetime(2026, 8, 25, 13, 0, tzinfo=UTC)


async def test_a_stale_update_does_not_overwrite_a_newer_amount():
    """The `applied_seq` guard again, on the other slice's write. Each slice
    carries its own copy of it now, so each needs its own reason not to drift."""

    await _project()
    await transaction_updated.UpdateProjectedTransactionAmount().apply(
        make_event(make_transaction_updated(new_amount="200.00"), outbox_seq=5)
    )

    await transaction_updated.UpdateProjectedTransactionAmount().apply(
        make_event(make_transaction_updated(new_amount="1.00"), outbox_seq=2)
    )

    transaction = await _load_transaction()
    assert transaction is not None
    assert transaction.amount == Decimal("200.00")


async def test_a_re_dispatch_after_an_update_re_values_the_legs_and_the_balances():
    await _seed_accounts()
    await _project()
    await _dispatch_created()

    updated = make_event(make_transaction_updated(new_amount="200.00"), outbox_seq=2)
    await transaction_updated.UpdateProjectedTransactionAmount().apply(updated)
    await transaction_updated.DispatchPostings(
        build_updated_dispatcher, exchange_rates=FixedRates()
    ).apply(updated)

    entries = await _load_entries()
    assert {entry.amount for entry in entries} == {Decimal("200.00")}
    assert (await _balances())[_template_key(0)] == Decimal("-200.00")


async def test_dispatched_entries_are_denominated_in_the_transaction_s_currency():
    """The end of the wire: a currency that left write-service on
    `TransactionCreated` has to reach the ledger rows, not stop at the
    projection."""

    await _seed_accounts()
    await _project(currency_code="JPY")
    await _dispatch_created()

    assert {entry.currency_code for entry in await _load_entries()} == {"JPY"}


async def test_a_transaction_projected_without_a_currency_stores_undenominated_entries():
    """Rows projected before the field existed carry an empty code. The ledger
    records that as unknown rather than guessing a currency for them."""

    await _seed_accounts()
    await _project(currency_code="")
    await _dispatch_created()

    assert {entry.currency_code for entry in await _load_entries()} == {None}


async def test_a_re_dispatch_after_an_update_keeps_the_original_currency():
    """`TransactionUpdated` carries no currency and does not need to: the
    updating slice reads it back from the projection the creating slice wrote.
    A transaction cannot change container, so it cannot change currency."""

    await _seed_accounts()
    await _project(currency_code="JPY")
    await _dispatch_created()

    updated = make_event(make_transaction_updated(new_amount="200.00"), outbox_seq=2)
    await transaction_updated.UpdateProjectedTransactionAmount().apply(updated)
    await transaction_updated.DispatchPostings(
        build_updated_dispatcher, exchange_rates=FixedRates()
    ).apply(updated)

    entries = await _load_entries()
    assert {entry.amount for entry in entries} == {Decimal("200.00")}
    assert {entry.currency_code for entry in entries} == {"JPY"}


async def test_a_stale_delete_does_not_bury_a_newer_projection():
    """The third copy of the `applied_seq` guard, on the deleting slice's write."""

    await transaction_created.ProjectTransaction().apply(
        make_event(make_transaction_created(), outbox_seq=5)
    )

    await transaction_deleted.SoftDeleteProjectedTransaction().apply(
        make_event(make_transaction_deleted(), outbox_seq=2)
    )

    transaction = await _load_transaction()
    assert transaction is not None
    assert transaction.deleted_at is None


async def test_a_delete_removes_the_legs_and_keeps_the_transaction():
    await _seed_accounts()
    await _project()
    await _dispatch_created()

    event = make_event(make_transaction_deleted(), outbox_seq=3)
    await transaction_deleted.RemovePostings().apply(event)
    await transaction_deleted.SoftDeleteProjectedTransaction().apply(event)

    transaction = await _load_transaction()
    assert await _count(EntryModel) == 0
    assert transaction is not None
    assert transaction.deleted_at == datetime(2026, 8, 25, 14, 0, tzinfo=UTC)


async def test_a_delete_leaves_the_accounts_standing_and_zeroes_their_balances():
    """An account belongs to the user, not to the transaction that first posted
    into it. Its balance, though, is made of entries that have just gone."""

    await _seed_accounts()
    await _project()
    await _dispatch_created()

    await transaction_deleted.RemovePostings().apply(
        make_event(make_transaction_deleted(), outbox_seq=3)
    )

    assert await _count(AccountModel) == len(CREATED_TEMPLATE_ACCOUNTS)
    assert set((await _balances()).values()) == {Decimal("0.00")}


async def test_a_deleted_transaction_is_not_dispatched_again():
    await _seed_accounts()
    await _project()
    await transaction_deleted.SoftDeleteProjectedTransaction().apply(
        make_event(make_transaction_deleted(), outbox_seq=3)
    )

    await _dispatch_created()

    assert await _count(EntryModel) == 0


async def test_the_injected_dispatcher_is_the_one_that_is_asked():
    await _seed_accounts()
    await _project()

    async with session_scope() as session:
        account_id = (
            await session.execute(select(AccountModel.id).where(AccountModel.group == "assets"))
        ).scalar_one()
    dispatcher = SingleLegDispatcher(account_id)

    await _dispatch_created(lambda _accounts: dispatcher)

    assert dispatcher.calls == [TRANSACTION_ID]


async def test_entries_record_what_was_spent_and_what_it_is_worth():
    """The ledger keeps both: 125 JPY is what happened, and its USD value is
    what the books add up. Neither is derivable from the other later without
    the rate, which is why the rate is stored beside them."""

    await _seed_accounts()
    await _project(currency_code="JPY")
    await _dispatch_created(rates=FixedRates(Decimal("0.0067")))

    entries = await _load_entries()

    assert {entry.amount for entry in entries} == {Decimal("125.00")}
    assert {entry.currency_code for entry in entries} == {"JPY"}
    assert {entry.book_amount for entry in entries} == {Decimal("0.84")}
    assert {entry.book_currency for entry in entries} == {"USD"}
    assert {entry.conversion_rate for entry in entries} == {Decimal("0.0067")}


async def test_balances_are_the_booked_value_not_the_spent_amount():
    """The whole point of booking: a balance folds USD, so wallets in different
    currencies can be added together at all."""

    await _seed_accounts()
    await _project(currency_code="JPY")
    await _dispatch_created(rates=FixedRates(Decimal("0.0067")))

    assert (await _balances())[_template_key(0)] == Decimal("-0.84")


async def test_seeded_accounts_are_denominated_in_the_book_currency():
    await _seed_accounts()

    async with session_scope() as session:
        rows = await session.execute(select(AccountModel.currency_code))
        assert set(rows.scalars()) == {"USD"}


async def test_a_re_dispatch_re_books_at_the_rate_of_the_day():
    """Postings are replaced wholesale, so a re-dispatch re-values them. The
    stored rate is what makes the change explainable rather than mysterious."""

    await _seed_accounts()
    await _project(currency_code="JPY")
    await _dispatch_created(rates=FixedRates(Decimal("0.0067")))

    await _dispatch_created(rates=FixedRates(Decimal("0.0100")))

    entries = await _load_entries()
    assert {entry.book_amount for entry in entries} == {Decimal("1.25")}
    assert {entry.conversion_rate for entry in entries} == {Decimal("0.0100")}
    assert (await _balances())[_template_key(0)] == Decimal("-1.25")


async def test_an_updated_transaction_re_books_its_balances_too():
    """The updating slice carries its own copy of the balance rule, so it needs
    its own reason not to drift back to folding the spent amount."""

    await _seed_accounts()
    await _project(currency_code="JPY")
    await _dispatch_created(rates=FixedRates(Decimal("0.0067")))

    updated = make_event(make_transaction_updated(new_amount="200.00"), outbox_seq=2)
    await transaction_updated.UpdateProjectedTransactionAmount().apply(updated)
    await transaction_updated.DispatchPostings(
        build_updated_dispatcher, exchange_rates=FixedRates(Decimal("0.0100"))
    ).apply(updated)

    entries = await _load_entries()
    assert {entry.amount for entry in entries} == {Decimal("200.00")}
    assert {entry.book_amount for entry in entries} == {Decimal("2.00")}
    assert (await _balances())[_template_key(0)] == Decimal("-2.00")


async def test_a_deleted_transaction_is_not_re_dispatched_by_an_update():
    """The updating slice carries its own copy of the soft-delete guard, so it
    needs its own reason not to lose it: an amount change arriving after a
    cancellation must not resurrect the postings."""

    await _seed_accounts()
    await _project()
    await transaction_deleted.SoftDeleteProjectedTransaction().apply(
        make_event(make_transaction_deleted(), outbox_seq=3)
    )

    updated = make_event(make_transaction_updated(new_amount="200.00"), outbox_seq=4)
    await transaction_updated.DispatchPostings(
        build_updated_dispatcher, exchange_rates=FixedRates()
    ).apply(updated)

    assert await _count(EntryModel) == 0

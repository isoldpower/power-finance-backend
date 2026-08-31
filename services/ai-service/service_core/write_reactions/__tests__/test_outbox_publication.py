"""What this service publishes, read back out of the outbox table.

Assertions are about the rows Debezium will tail, not about the effects' return
values: the payload shape, the partition key and the order are the contract, and
all three are decided at the moment the row is written.
"""

from uuid import UUID

import pytest
from kafka_consumer_py.fakes import make_event
from sqlalchemy import delete, func, select

from service_core.shared.db_connection import (
    EntryModel,
    OutboxEntryModel,
    UserModel,
    session_scope,
)
from service_core.write_reactions import (
    transaction_created,
    transaction_deleted,
    transaction_updated,
    user_created,
)

from ..transaction_created.__tests__.fakes import FixedRates
from .fakes import (
    EXTERNAL_ID,
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


async def _outbox() -> list[OutboxEntryModel]:
    """Every published row, in the order a consumer will see it."""

    async with session_scope() as session:
        rows = await session.execute(select(OutboxEntryModel).order_by(OutboxEntryModel.id))
        return list(rows.scalars())


async def _published_types() -> list[str]:
    return [row.event_type for row in await _outbox()]


async def _count(model) -> int:
    async with session_scope() as session:
        return (await session.execute(select(func.count()).select_from(model))).scalar_one()


async def _clear_outbox() -> None:
    async with session_scope() as session:
        await session.execute(delete(OutboxEntryModel))


async def _seed() -> None:
    await user_created.SeedTemplateAccounts(SEED_TEMPLATE_ACCOUNTS).apply(
        make_event(make_user_synced())
    )


async def _project() -> None:
    await transaction_created.ProjectTransaction().apply(
        make_event(make_transaction_created(), outbox_seq=1)
    )


async def _dispatch() -> None:
    await transaction_created.DispatchPostings(
        build_created_dispatcher, exchange_rates=FixedRates()
    ).apply(make_event(make_transaction_created(), outbox_seq=1))


async def test_seeding_publishes_one_account_created_per_account():
    await _seed()

    rows = await _outbox()

    assert [row.event_type for row in rows] == ["AccountCreated"] * len(CREATED_TEMPLATE_ACCOUNTS)
    assert {row.payload["name"] for row in rows} == {
        account.specification.name for account in CREATED_TEMPLATE_ACCOUNTS
    }


async def test_a_redelivered_sync_publishes_nothing_the_second_time():
    """`ensure` reports only what it inserted, so a replay is silent rather than
    announcing accounts that already existed."""

    await _seed()
    await _clear_outbox()

    await _seed()

    assert await _published_types() == []


async def test_the_external_id_is_remembered_and_becomes_the_partition_key():
    await _seed()

    async with session_scope() as session:
        user = await session.get(UserModel, USER_ID)

    assert user is not None
    assert user.external_id == EXTERNAL_ID
    assert {row.partition_key for row in await _outbox()} == {EXTERNAL_ID}


async def test_the_account_group_travels_as_its_enum_name():
    """The payload is proto JSON, so the group arrives upper-case and prefixed
    rather than as the lower-case string the table stores."""

    await _seed()

    groups = {row.payload["account_group"] for row in await _outbox()}

    assert groups == {"ACCOUNT_GROUP_LIABILITIES", "ACCOUNT_GROUP_ASSETS"}


async def test_a_balance_change_names_its_group_by_the_same_enum():
    """Each slice carries its own copy of the stored-group -> proto-enum map, so
    a copy that drifts from the spelling the table uses would quietly publish
    `ACCOUNT_GROUP_WRONG`. This covers the dispatching slice's copy; the test
    above covers the seeding slice's."""

    await _seed()
    await _project()
    await _clear_outbox()

    await _dispatch()

    groups = {
        row.payload["account_group"]
        for row in await _outbox()
        if row.event_type == "AccountUpdated"
    }
    assert groups == {"ACCOUNT_GROUP_LIABILITIES", "ACCOUNT_GROUP_ASSETS"}


async def test_a_re_dispatch_names_its_group_by_the_same_enum():
    """And the re-dispatching slice's copy."""

    await _seed()
    await _project()
    await _dispatch()
    await _clear_outbox()

    updated = make_event(make_transaction_updated(new_amount="200.00"), outbox_seq=2)
    await transaction_updated.UpdateProjectedTransactionAmount().apply(updated)
    await transaction_updated.DispatchPostings(
        build_updated_dispatcher, exchange_rates=FixedRates()
    ).apply(updated)

    groups = {
        row.payload["account_group"]
        for row in await _outbox()
        if row.event_type == "AccountUpdated"
    }
    assert groups == {"ACCOUNT_GROUP_LIABILITIES", "ACCOUNT_GROUP_ASSETS"}


async def test_a_deletion_names_its_group_by_the_same_enum():
    """And the deleting slice's third copy."""

    await _seed()
    await _project()
    await _dispatch()
    await _clear_outbox()

    await transaction_deleted.RemovePostings().apply(
        make_event(make_transaction_deleted(), outbox_seq=3)
    )

    groups = {
        row.payload["account_group"]
        for row in await _outbox()
        if row.event_type == "AccountUpdated"
    }
    assert groups == {"ACCOUNT_GROUP_LIABILITIES", "ACCOUNT_GROUP_ASSETS"}


async def test_a_dispatch_publishes_its_legs_then_the_marker_then_the_balances():
    await _seed()
    await _project()
    await _clear_outbox()

    await _dispatch()

    assert await _published_types() == [
        "AccountPostingCreated",
        "AccountPostingCreated",
        "AccountPostingsDispatched",
        "AccountUpdated",
        "AccountUpdated",
    ]


async def test_every_event_of_one_dispatch_shares_a_dispatch_id():
    await _seed()
    await _project()
    await _clear_outbox()

    await _dispatch()

    rows = [row for row in await _outbox() if row.event_type.startswith("AccountPosting")]

    assert len({row.payload["dispatch_id"] for row in rows}) == 1


async def test_the_marker_counts_both_sides_of_the_replacement():
    await _seed()
    await _project()
    await _dispatch()
    await _clear_outbox()

    # The second dispatch replaces the first one's legs, so it has both a
    # removal count and a creation count to report.
    await _dispatch()

    marker = next(row for row in await _outbox() if row.event_type == "AccountPostingsDispatched")

    assert marker.payload["deleted_count"] == len(CREATED_TEMPLATE_ACCOUNTS)
    assert marker.payload["created_count"] == len(CREATED_TEMPLATE_ACCOUNTS)
    assert marker.payload["backend"] == "template"
    assert marker.payload["balanced"] is True


async def test_a_re_dispatch_that_moves_no_balance_announces_no_account_update():
    """The reason `recompute_balances` reports moves rather than touches: the
    legs are rewritten with new ids, but the balances land where they already
    were, and an `AccountUpdated` saying nothing changed is a lie consumers
    would have to diff to catch."""

    await _seed()
    await _project()
    await _dispatch()
    await _clear_outbox()

    await _dispatch()

    assert "AccountUpdated" not in await _published_types()


async def test_a_posting_payload_carries_the_leg_as_stored():
    await _seed()
    await _project()
    await _clear_outbox()

    await _dispatch()

    leg = next(row for row in await _outbox() if row.event_type == "AccountPostingCreated")

    assert leg.payload["transaction_id"] == str(TRANSACTION_ID)
    assert leg.payload["user_id"] == USER_ID
    assert leg.payload["amount"] == "125.00"
    assert leg.payload["currency_code"] == "EUR"
    assert UUID(leg.payload["posting_id"])


async def test_a_delete_publishes_removals_and_a_marker_with_no_backend():
    await _seed()
    await _project()
    await _dispatch()
    await _clear_outbox()

    await transaction_deleted.RemovePostings().apply(
        make_event(make_transaction_deleted(), outbox_seq=2)
    )

    rows = await _outbox()
    marker = next(row for row in rows if row.event_type == "AccountPostingsDispatched")

    assert [row.event_type for row in rows] == [
        "AccountPostingDeleted",
        "AccountPostingDeleted",
        "AccountPostingsDispatched",
        "AccountUpdated",
        "AccountUpdated",
    ]
    assert marker.payload["deleted_count"] == len(CREATED_TEMPLATE_ACCOUNTS)
    assert marker.payload["created_count"] == 0
    assert marker.payload["backend"] == ""


async def test_a_delete_with_nothing_to_remove_publishes_nothing():
    await _seed()
    await _project()

    await _clear_outbox()
    await transaction_deleted.RemovePostings().apply(
        make_event(make_transaction_deleted(), outbox_seq=2)
    )

    assert await _published_types() == []


async def test_a_dispatch_for_a_user_with_no_known_external_id_retries():
    """Only reachable for a user seeded before the external id was projected;
    `UnknownUserError` is not a `PoisonError`, so the event comes back."""

    await _seed()
    await _project()

    async with session_scope() as session:
        await session.execute(delete(UserModel))

    with pytest.raises(transaction_created.UnknownUserError):
        await _dispatch()


async def test_nothing_is_published_when_the_transaction_rolls_back():
    """The invariant the outbox exists for. The rows are really written — the
    failure happens after `publish` returns — so only the shared transaction
    can take them back, and the legs go with them."""

    await _seed()
    await _project()
    await _clear_outbox()

    with pytest.raises(RuntimeError, match="published then blew up"):
        await transaction_created.DispatchPostings(
            build_created_dispatcher,
            _SabotagedUnitOfWork,
            exchange_rates=FixedRates(),
        ).apply(make_event(make_transaction_created(), outbox_seq=1))

    assert await _published_types() == []
    assert await _count(EntryModel) == 0


class _ExplodingOutbox:
    """Writes the rows, then fails. The rows exist in the transaction at the
    moment it unwinds, which is the only way to tell a rollback from a publish
    that never happened."""

    def __init__(self, inner):
        self._inner = inner

    async def publish(self, entries):
        await self._inner.publish(entries)
        raise RuntimeError("published then blew up")


class _SabotagedUnitOfWork(transaction_created.SqlAlchemyDispatchUnitOfWork):
    @property
    def outbox(self):
        return _ExplodingOutbox(super().outbox)

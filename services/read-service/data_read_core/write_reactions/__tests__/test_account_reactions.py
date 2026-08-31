"""The ledger ai-service publishes, landing in the read models.

These five events come from a different service and a different outbox than
everything else this consumer handles, so the assertions here are as much about
where they must *not* reach as about what they project.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from background_workers.services.build_event_router import _subscribe_all_events
from fakes import make_event
from google.protobuf.timestamp_pb2 import Timestamp
from kafka_consumer_py import KafkaEventRouter
from kafka_messages import (
    AccountCreated,
    AccountGroup,
    AccountPostingCreated,
    AccountPostingDeleted,
    AccountPostingsDispatched,
    AccountUpdated,
)

from data_read_core.shared.postgres_orm import (
    AccountDispatchReadModel,
    AccountPostingReadModel,
    AccountReadModel,
)
from data_read_core.shared.read_at_least import AppliedOutboxSeq
from data_read_core.write_reactions import (
    CreateAccountPostingReadModel,
    CreateAccountReadModel,
    RecordAccountDispatch,
    RemoveAccountPostingReadModel,
    UpdateAccountReadModel,
)

pytestmark = pytest.mark.django_db(transaction=True)

USER_ID = 7
EXTERNAL_ID = "clerk_7"
ACCOUNT_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
OTHER_ACCOUNT_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
POSTING_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
TRANSACTION_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
DISPATCH_ID = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"


def _ts(when: datetime | None = None) -> Timestamp:
    timestamp = Timestamp()
    timestamp.FromDatetime(when or datetime.now(UTC))
    return timestamp


def _account_created(
    *,
    account_id: str = ACCOUNT_ID,
    group: int = AccountGroup.ACCOUNT_GROUP_ASSETS,
    name: str = "temporary-assets",
    balance: str = "0.00",
) -> AccountCreated:
    return AccountCreated(
        event_id="evt-a",
        account_id=account_id,
        user_external_id=EXTERNAL_ID,
        user_id=USER_ID,
        account_group=group,
        name=name,
        balance=balance,
        created_at=_ts(datetime(2026, 8, 25, 12, 0, tzinfo=UTC)),
    )


def _posting_created(*, posting_id: str = POSTING_ID, debit: bool = True) -> AccountPostingCreated:
    return AccountPostingCreated(
        event_id="evt-p",
        posting_id=posting_id,
        dispatch_id=DISPATCH_ID,
        account_id=ACCOUNT_ID,
        transaction_id=TRANSACTION_ID,
        user_external_id=EXTERNAL_ID,
        user_id=USER_ID,
        amount="125.00",
        title="Groceries",
        icon="",
        debit=debit,
        currency_code="JPY",
        position=0,
        created_at=_ts(datetime(2026, 8, 25, 12, 0, tzinfo=UTC)),
    )


async def test_a_created_account_lands_in_the_chart():
    await CreateAccountReadModel().apply(make_event(_account_created(), outbox_seq=1))

    account = await AccountReadModel.objects.aget(id=ACCOUNT_ID)

    assert account.user_id == USER_ID
    assert account.group == "assets"
    assert account.name == "temporary-assets"
    assert account.created_at == datetime(2026, 8, 25, 12, 0, tzinfo=UTC)


async def test_the_proto_group_becomes_its_stored_spelling():
    await CreateAccountReadModel().apply(
        make_event(
            _account_created(group=AccountGroup.ACCOUNT_GROUP_LIABILITIES, name="owed"),
            outbox_seq=1,
        )
    )

    assert (await AccountReadModel.objects.aget(id=ACCOUNT_ID)).group == "liabilities"


async def test_an_account_with_no_usable_group_is_stored_ungrouped():
    """`ACCOUNT_GROUP_WRONG` is the proto zero value. Filing it under a real
    group would put it on the wrong side of the ledger; blank says unknown."""

    await CreateAccountReadModel().apply(
        make_event(
            _account_created(group=AccountGroup.ACCOUNT_GROUP_WRONG, name="mystery"),
            outbox_seq=1,
        )
    )

    assert (await AccountReadModel.objects.aget(id=ACCOUNT_ID)).group == ""


async def test_projecting_the_same_account_twice_leaves_one_row():
    await CreateAccountReadModel().apply(make_event(_account_created(), outbox_seq=1))
    await CreateAccountReadModel().apply(make_event(_account_created(), outbox_seq=1))

    assert await AccountReadModel.objects.acount() == 1


async def test_an_update_restates_the_balance():
    await CreateAccountReadModel().apply(make_event(_account_created(), outbox_seq=1))

    await UpdateAccountReadModel().apply(
        make_event(
            AccountUpdated(
                event_id="evt-u",
                account_id=ACCOUNT_ID,
                user_external_id=EXTERNAL_ID,
                user_id=USER_ID,
                previous_balance="0.00",
                new_balance="125.00",
                account_group=AccountGroup.ACCOUNT_GROUP_ASSETS,
                name="temporary-assets",
                updated_at=_ts(datetime(2026, 8, 25, 13, 0, tzinfo=UTC)),
            ),
            outbox_seq=2,
        )
    )

    account = await AccountReadModel.objects.aget(id=ACCOUNT_ID)
    assert account.balance == Decimal("125.00")
    assert account.updated_at == datetime(2026, 8, 25, 13, 0, tzinfo=UTC)


async def test_an_update_for_an_unseen_account_still_lands():
    """`AccountUpdated` carries the whole row, so a projection that started
    after the account was created heals instead of leaving postings pointing at
    an account missing from the chart."""

    await UpdateAccountReadModel().apply(
        make_event(
            AccountUpdated(
                event_id="evt-u",
                account_id=ACCOUNT_ID,
                user_external_id=EXTERNAL_ID,
                user_id=USER_ID,
                previous_balance="0.00",
                new_balance="40.00",
                account_group=AccountGroup.ACCOUNT_GROUP_EQUITY,
                name="opening-balance",
                updated_at=_ts(),
            ),
            outbox_seq=2,
        )
    )

    account = await AccountReadModel.objects.aget(id=ACCOUNT_ID)
    assert account.group == "equity"
    assert account.balance == Decimal("40.00")


async def test_a_posting_lands_with_its_own_currency():
    await CreateAccountPostingReadModel().apply(make_event(_posting_created(), outbox_seq=3))

    posting = await AccountPostingReadModel.objects.aget(id=POSTING_ID)

    assert posting.transaction_id == UUID(TRANSACTION_ID)
    assert posting.amount == Decimal("125.00")
    assert posting.currency_code == "JPY"
    assert posting.debit is True


async def test_a_credited_posting_keeps_its_side():
    await CreateAccountPostingReadModel().apply(
        make_event(_posting_created(debit=False), outbox_seq=3)
    )

    assert (await AccountPostingReadModel.objects.aget(id=POSTING_ID)).debit is False


async def test_redelivering_a_posting_leaves_one_row():
    await CreateAccountPostingReadModel().apply(make_event(_posting_created(), outbox_seq=3))
    await CreateAccountPostingReadModel().apply(make_event(_posting_created(), outbox_seq=3))

    assert await AccountPostingReadModel.objects.acount() == 1


async def test_a_deleted_posting_leaves_the_table():
    await CreateAccountPostingReadModel().apply(make_event(_posting_created(), outbox_seq=3))

    await RemoveAccountPostingReadModel().apply(
        make_event(
            AccountPostingDeleted(
                event_id="evt-d",
                posting_id=POSTING_ID,
                dispatch_id=DISPATCH_ID,
                account_id=ACCOUNT_ID,
                transaction_id=TRANSACTION_ID,
                user_external_id=EXTERNAL_ID,
                user_id=USER_ID,
                deleted_at=_ts(),
            ),
            outbox_seq=4,
        )
    )

    assert await AccountPostingReadModel.objects.acount() == 0


def _dispatched(*, balanced: bool = True, comment: str = "") -> AccountPostingsDispatched:
    return AccountPostingsDispatched(
        event_id="evt-x",
        dispatch_id=DISPATCH_ID,
        transaction_id=TRANSACTION_ID,
        user_external_id=EXTERNAL_ID,
        user_id=USER_ID,
        deleted_count=0,
        created_count=2,
        balanced=balanced,
        comment=comment,
        backend="template",
        dispatched_at=_ts(),
    )


async def test_the_dispatch_verdict_is_recorded():
    await RecordAccountDispatch().apply(make_event(_dispatched(), outbox_seq=5))

    verdict = await AccountDispatchReadModel.objects.aget(transaction_id=TRANSACTION_ID)

    assert verdict.balanced is True
    assert verdict.backend == "template"
    assert verdict.created_count == 2


async def test_a_re_dispatch_replaces_the_verdict_rather_than_adding_one():
    await RecordAccountDispatch().apply(make_event(_dispatched(), outbox_seq=5))
    await RecordAccountDispatch().apply(
        make_event(_dispatched(balanced=False, comment="legs disagree"), outbox_seq=6)
    )

    assert await AccountDispatchReadModel.objects.acount() == 1

    verdict = await AccountDispatchReadModel.objects.aget(transaction_id=TRANSACTION_ID)
    assert verdict.balanced is False
    assert verdict.comment == "legs disagree"


async def test_account_events_never_advance_read_your_writes():
    """The whole reason these are not wrapped in `TrackAppliedSeq`. That table
    holds one high-water mark per user of the *write-service* outbox sequence;
    ai-service numbers its outbox independently, so letting these through would
    tell a client its own pending write had already landed."""

    router = KafkaEventRouter()
    _subscribe_all_events(router)

    await router.dispatch(make_event(_account_created(), outbox_seq=999_999))

    assert await AccountReadModel.objects.acount() == 1
    assert not await AppliedOutboxSeq.objects.filter(user_id=USER_ID).aexists()

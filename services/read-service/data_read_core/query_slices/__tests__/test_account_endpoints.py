"""The ledger over HTTP: the chart and its filters, one account with its
history, and the postings the transaction detail has always promised."""

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from background_workers.services.build_event_router import _subscribe_all_events
from django.contrib.auth import get_user_model
from django.test import AsyncClient
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

from data_read_core.shared.exchange_rates import get_rate_service
from data_read_core.shared.money import CURRENCY_CATALOG
from data_read_core.shared.postgres_orm import (
    NO_CHAIN_SENTINEL,
    AccountDispatchReadModel,
    AccountPostingReadModel,
    AccountReadModel,
    CurrencyReadModel,
    TransactionReadModel,
    WalletReadModel,
)
from data_read_core.shared.redis_cache import get_redis

pytestmark = pytest.mark.django_db(transaction=True)

EXTERNAL_USER_ID = "user_ledger"
OTHER_USER_ID = "user_intruder"
AUTH_HEADERS = {"X-User-Id": EXTERNAL_USER_ID}
WALLET_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
CACHE_PREFIXES = (
    "read:accounts:*",
    "read:account:*",
    "ver:accounts:*",
    "read:transaction:*",
    "read:rates:*",
)


def _timestamp() -> Timestamp:
    stamp = Timestamp()
    stamp.FromDatetime(datetime(2026, 8, 25, 12, 0, tzinfo=UTC))
    return stamp


def as_user(path: str, headers: dict | None = None):
    return AsyncClient().get(path, headers=headers or AUTH_HEADERS)


def body_of(response) -> dict:
    return json.loads(response.content)


@pytest.fixture(autouse=True)
async def _empty_cache():
    async def clear() -> None:
        # The rate service holds a Redis client of its own. Clearing only
        # `get_redis` would leave it wired to the connection this fixture is
        # about to close.
        get_rate_service.cache_clear()
        get_redis.cache_clear()
        redis = get_redis()
        for pattern in CACHE_PREFIXES:
            async for key in redis.scan_iter(match=pattern):
                await redis.delete(key)

    await clear()
    yield
    await clear()
    await get_redis().aclose()
    get_rate_service.cache_clear()
    get_redis.cache_clear()


@pytest.fixture(autouse=True)
async def _provisioned():
    CURRENCY_CATALOG.reset()
    user = await get_user_model().objects.acreate(username=EXTERNAL_USER_ID)
    await get_user_model().objects.acreate(username=OTHER_USER_ID)
    await CurrencyReadModel.objects.abulk_create(
        [
            CurrencyReadModel(code="USD", name="US Dollar", symbol="$", numeric="840", digits=2),
            CurrencyReadModel(code="JPY", name="Yen", symbol="¥", numeric="392", digits=0),
        ],
        ignore_conflicts=True,
    )
    await WalletReadModel.objects.acreate(
        id=WALLET_ID,
        user_id=user.id,
        title="Main",
        currency_code="USD",
        balance=Decimal("0"),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    yield
    CURRENCY_CATALOG.reset()


async def _user_id(username: str = EXTERNAL_USER_ID) -> int:
    user = await get_user_model().objects.aget(username=username)
    return user.id


async def _account(
    *,
    group: str = "assets",
    name: str = "temporary-assets",
    balance: str = "0.00",
    currency: str = "USD",
    owner: str = EXTERNAL_USER_ID,
    created_at: datetime = datetime(2026, 8, 25, 12, 0, tzinfo=UTC),
) -> AccountReadModel:
    return await AccountReadModel.objects.acreate(
        id=uuid.uuid4(),
        user_id=await _user_id(owner),
        group=group,
        name=name,
        balance=Decimal(balance),
        currency_code=currency,
        created_at=created_at,
    )


async def _transaction(**overrides) -> TransactionReadModel:
    created_at = datetime(2026, 8, 12, 11, 51, tzinfo=UTC)
    return await TransactionReadModel.objects.acreate(
        id=uuid.uuid4(),
        wallet_id=WALLET_ID,
        wallet_name="Main",
        user_id=await _user_id(),
        amount=Decimal("-50.00"),
        currency_code="USD",
        name="Groceries",
        chain_sort=NO_CHAIN_SENTINEL,
        occurred_at=created_at,
        created_at=created_at,
        **overrides,
    )


async def _posting(
    *,
    account: AccountReadModel,
    transaction: TransactionReadModel,
    debit: bool = True,
    amount: str = "125.00",
    currency: str = "JPY",
    position: int = 0,
    created_at: datetime = datetime(2026, 8, 25, 12, 0, tzinfo=UTC),
) -> AccountPostingReadModel:
    return await AccountPostingReadModel.objects.acreate(
        id=uuid.uuid4(),
        user_id=account.user_id,
        account_id=account.id,
        transaction_id=transaction.id,
        dispatch_id=uuid.uuid4(),
        title="Groceries",
        debit=debit,
        amount=Decimal(amount),
        currency_code=currency,
        position=position,
        created_at=created_at,
    )


async def test_the_chart_lists_the_user_s_accounts():
    await _account(group="assets", name="temporary-assets", balance="125.00")
    await _account(group="liabilities", name="temporary-liability", balance="-125.00")

    payload = body_of(await as_user("/api/v1/accounts"))

    assert {(row["group"], row["name"], row["money"]["amount"]) for row in payload["data"]} == {
        ("assets", "temporary-assets", "125.00"),
        ("liabilities", "temporary-liability", "-125.00"),
    }


async def test_a_balance_is_money_in_the_book_currency():
    """The balance is a sum of converted legs, so it carries the currency it
    was summed in — a bare decimal string would leave a client guessing."""

    await _account(balance="125.00", currency="USD")

    payload = body_of(await as_user("/api/v1/accounts"))

    assert payload["data"][0]["money"] == {"amount": "125.00", "currency": "USD"}


async def test_the_chart_is_ordered_newest_first_not_by_group():
    """`group` filters; it does not order. Assets do not lead liabilities."""

    await _account(
        group="assets",
        name="oldest",
        created_at=datetime(2026, 8, 20, tzinfo=UTC),
    )
    await _account(
        group="liabilities",
        name="newest",
        created_at=datetime(2026, 8, 26, tzinfo=UTC),
    )
    await _account(
        group="assets",
        name="middle",
        created_at=datetime(2026, 8, 22, tzinfo=UTC),
    )

    payload = body_of(await as_user("/api/v1/accounts"))

    assert [row["name"] for row in payload["data"]] == ["newest", "middle", "oldest"]


async def test_the_group_filter_narrows_the_page():
    await _account(group="assets", name="owned")
    await _account(group="liabilities", name="owed")

    payload = body_of(await as_user("/api/v1/accounts?group=liabilities"))

    assert [row["name"] for row in payload["data"]] == ["owed"]
    assert payload["meta"]["group"] == "liabilities"


async def test_an_unknown_group_is_rejected():
    response = await as_user("/api/v1/accounts?group=receivables")

    assert response.status_code == 422
    assert body_of(response)["error"]["code"] == "validation_failed"


async def test_the_group_counts_ignore_the_group_filter():
    """The tab labels have to hold still when a tab is selected, so `groups`
    describes the whole chart no matter what `group` narrowed the page to."""

    await _account(group="assets", name="one")
    await _account(group="assets", name="two")
    await _account(group="liabilities", name="owed")

    payload = body_of(await as_user("/api/v1/accounts?group=liabilities"))

    assert payload["meta"]["total"] == 1
    assert payload["meta"]["groups"] == {"assets": 2, "liabilities": 1, "equity": 0}


async def test_the_lowbar_hides_small_accounts():
    await _account(name="material", balance="500.00")
    await _account(name="rounding-dust", balance="0.40")

    payload = body_of(await as_user("/api/v1/accounts?lowbar=1.00"))

    assert [row["name"] for row in payload["data"]] == ["material"]


async def test_the_lowbar_compares_magnitudes_so_it_keeps_liabilities():
    """A liability's balance is negative. A signed comparison would drop the
    whole group the moment a client set any threshold at all."""

    await _account(group="liabilities", name="owed", balance="-500.00")
    await _account(group="liabilities", name="trivial", balance="-0.40")

    payload = body_of(await as_user("/api/v1/accounts?lowbar=1.00"))

    assert [row["name"] for row in payload["data"]] == ["owed"]


async def test_the_lowbar_and_its_currency_are_echoed_back():
    await _account(balance="500.00")

    payload = body_of(await as_user("/api/v1/accounts?lowbar=1&currency=USD"))

    assert payload["meta"]["lowbar"] == "1.00"
    assert payload["meta"]["currency"] == "USD"


async def test_the_default_threshold_excludes_nothing():
    await _account(name="empty", balance="0.00")

    payload = body_of(await as_user("/api/v1/accounts"))

    assert [row["name"] for row in payload["data"]] == ["empty"]
    assert payload["meta"]["lowbar"] == "0.00"
    assert payload["meta"]["group"] == "all"


async def test_a_lowbar_past_its_currency_s_scale_is_rejected():
    response = await as_user("/api/v1/accounts?lowbar=1.005&currency=USD")

    assert response.status_code == 422
    assert body_of(response)["error"]["details"][0]["code"] == "amount_precision"


async def test_an_unsupported_lowbar_currency_is_rejected():
    response = await as_user("/api/v1/accounts?lowbar=1&currency=XYZ")

    assert response.status_code == 422
    assert body_of(response)["error"]["code"] == "unsupported_currency"


async def test_a_lowbar_in_another_currency_is_converted_before_it_compares():
    """The threshold arrives in the caller's currency and the balances are in
    the book currency, so one of the two has to move. Converting the threshold
    once is the half that a single index can still serve."""

    await _account(name="kept", balance="500.00", currency="USD")
    await _account(name="dropped", balance="0.50", currency="USD")

    response = await as_user("/api/v1/accounts?lowbar=100&currency=JPY")
    payload = body_of(response)
    assert response.status_code == 200, payload

    assert [row["name"] for row in payload["data"]] == ["kept"]


async def test_the_chart_does_not_show_someone_else_s_accounts():
    await _account(name="mine")
    await _account(name="theirs", owner=OTHER_USER_ID)

    payload = body_of(await as_user("/api/v1/accounts"))

    assert [row["name"] for row in payload["data"]] == ["mine"]


async def test_the_detail_embeds_the_legs_posted_into_the_account():
    account = await _account()
    transaction = await _transaction()
    await _posting(account=account, transaction=transaction)

    payload = body_of(await as_user(f"/api/v1/accounts/{account.id}"))

    history = payload["data"]["history"]
    assert len(history) == 1
    assert history[0]["debit"] is True
    assert history[0]["source_transaction"] == str(transaction.id)


async def test_the_history_is_paginated_under_its_own_meta_namespace():
    account = await _account()
    transaction = await _transaction()
    await _posting(
        account=account,
        transaction=transaction,
        created_at=datetime(2026, 8, 25, 12, 0, tzinfo=UTC),
    )
    await _posting(
        account=account,
        transaction=transaction,
        created_at=datetime(2026, 8, 26, 12, 0, tzinfo=UTC),
    )

    payload = body_of(await as_user(f"/api/v1/accounts/{account.id}?limit=1"))

    assert len(payload["data"]["history"]) == 1
    assert payload["meta"]["history"]["total"] == 2
    assert payload["meta"]["history"]["next_cursor"] is not None


async def test_a_history_entry_carries_an_id_the_cursor_can_anchor_on():
    """The target's example omits it; a keyset-paginated collection cannot."""

    account = await _account()
    transaction = await _transaction()
    posting = await _posting(account=account, transaction=transaction)

    payload = body_of(await as_user(f"/api/v1/accounts/{account.id}"))

    assert payload["data"]["history"][0]["id"] == str(posting.id)


async def test_history_entries_are_denominated_at_their_own_currency_s_scale():
    """The account's balance is in the book currency; each leg is in the
    currency of the transaction behind it — and JPY has no minor unit, so
    rendering it at two decimals would invent one."""

    account = await _account(currency="USD")
    transaction = await _transaction()
    await _posting(account=account, transaction=transaction, amount="125", currency="JPY")

    payload = body_of(await as_user(f"/api/v1/accounts/{account.id}"))

    assert payload["data"]["money"]["currency"] == "USD"
    assert payload["data"]["history"][0]["money"] == {"amount": "125", "currency": "JPY"}


async def test_someone_else_s_account_is_not_found():
    """A 404 rather than a 403: 403 would make every UUID path an existence
    oracle."""

    account = await _account(owner=OTHER_USER_ID)

    response = await as_user(f"/api/v1/accounts/{account.id}")

    assert response.status_code == 404


async def test_an_unknown_account_is_not_found():
    response = await as_user(f"/api/v1/accounts/{uuid.uuid4()}")

    assert response.status_code == 404


async def test_the_transaction_detail_carries_its_double_entry():
    """The payload has advertised `postings` since before there was a ledger
    to fill it from."""

    account = await _account(group="assets", name="temporary-assets")
    other = await _account(group="liabilities", name="temporary-liability")
    transaction = await _transaction()
    await _posting(account=account, transaction=transaction, debit=True, position=0)
    await _posting(account=other, transaction=transaction, debit=False, position=1)

    payload = body_of(await as_user(f"/api/v1/transactions/{transaction.id}"))

    postings = payload["data"]["postings"]
    assert [(leg["debit"], leg["position"]) for leg in postings] == [(True, 0), (False, 1)]
    assert postings[0]["account_id"] == str(account.id)
    assert postings[0]["money"] == {"amount": "125", "currency": "JPY"}


async def test_the_transaction_detail_reports_the_dispatch_verdict():
    transaction = await _transaction()
    await AccountDispatchReadModel.objects.acreate(
        transaction_id=transaction.id,
        user_id=await _user_id(),
        dispatch_id=uuid.uuid4(),
        balanced=False,
        comment="legs disagree",
        backend="template",
        created_count=2,
        deleted_count=0,
        dispatched_at=datetime(2026, 8, 25, 12, 0, tzinfo=UTC),
    )

    payload = body_of(await as_user(f"/api/v1/transactions/{transaction.id}"))

    assert payload["data"]["analysis"] == {"balanced": False, "comment": "legs disagree"}


async def test_a_transaction_the_ledger_has_not_reached_still_serves():
    """ai-service dispatches after the write returns, so a freshly created
    transaction is readable before its postings exist."""

    transaction = await _transaction()

    payload = body_of(await as_user(f"/api/v1/transactions/{transaction.id}"))

    assert payload["data"]["postings"] == []
    assert payload["data"]["analysis"] is None


async def test_a_new_posting_invalidates_the_cached_transaction_detail():
    """The postings ride inside the cached transaction DTO, so a dispatch that
    lands after the detail was first read has to evict it. Without that, the
    payload keeps advertising an empty ledger for the whole cache TTL — and the
    transaction row itself never changed, so nothing else would evict it."""

    account = await _account()
    transaction = await _transaction()

    first = body_of(await as_user(f"/api/v1/transactions/{transaction.id}"))
    assert first["data"]["postings"] == []

    await _dispatch(
        AccountPostingCreated(
            event_id="evt-p",
            posting_id=str(uuid.uuid4()),
            dispatch_id=str(uuid.uuid4()),
            account_id=str(account.id),
            transaction_id=str(transaction.id),
            user_external_id=EXTERNAL_USER_ID,
            user_id=account.user_id,
            amount="125",
            title="Groceries",
            debit=True,
            currency_code="JPY",
            position=0,
            created_at=_timestamp(),
        ),
        seq=10,
    )

    second = body_of(await as_user(f"/api/v1/transactions/{transaction.id}"))

    assert len(second["data"]["postings"]) == 1


async def _dispatch(message, seq: int) -> None:
    router = KafkaEventRouter()
    _subscribe_all_events(router)
    await router.dispatch(make_event(message, outbox_seq=seq))


async def test_a_removed_posting_invalidates_the_cached_transaction_detail():
    """The same staleness in reverse: a re-dispatch replaces legs, and a detail
    cached before it would keep serving postings that no longer exist."""

    account = await _account()
    transaction = await _transaction()
    posting = await _posting(account=account, transaction=transaction)

    first = body_of(await as_user(f"/api/v1/transactions/{transaction.id}"))
    assert len(first["data"]["postings"]) == 1

    await _dispatch(
        AccountPostingDeleted(
            event_id="evt-d",
            posting_id=str(posting.id),
            dispatch_id=str(uuid.uuid4()),
            account_id=str(account.id),
            transaction_id=str(transaction.id),
            user_external_id=EXTERNAL_USER_ID,
            user_id=account.user_id,
            deleted_at=_timestamp(),
        ),
        seq=11,
    )

    second = body_of(await as_user(f"/api/v1/transactions/{transaction.id}"))

    assert second["data"]["postings"] == []


async def test_a_dispatch_verdict_invalidates_the_cached_transaction_detail():
    transaction = await _transaction()

    first = body_of(await as_user(f"/api/v1/transactions/{transaction.id}"))
    assert first["data"]["analysis"] is None

    await _dispatch(
        AccountPostingsDispatched(
            event_id="evt-x",
            dispatch_id=str(uuid.uuid4()),
            transaction_id=str(transaction.id),
            user_external_id=EXTERNAL_USER_ID,
            user_id=await _user_id(),
            deleted_count=0,
            created_count=2,
            balanced=True,
            comment="",
            backend="template",
            dispatched_at=_timestamp(),
        ),
        seq=12,
    )

    second = body_of(await as_user(f"/api/v1/transactions/{transaction.id}"))

    assert second["data"]["analysis"] == {"balanced": True, "comment": None}


async def test_a_new_account_invalidates_the_cached_chart():
    """List pages are cached under a per-user version counter, so a chart read
    before the account existed would keep serving without it until the entry
    expired on its own."""

    first = body_of(await as_user("/api/v1/accounts"))
    assert first["data"] == []

    await _dispatch(
        AccountCreated(
            event_id="evt-a",
            account_id=str(uuid.uuid4()),
            user_external_id=EXTERNAL_USER_ID,
            user_id=await _user_id(),
            account_group=AccountGroup.ACCOUNT_GROUP_ASSETS,
            name="temporary-assets",
            balance="0.00",
            currency_code="USD",
            created_at=_timestamp(),
        ),
        seq=13,
    )

    second = body_of(await as_user("/api/v1/accounts"))

    assert [row["name"] for row in second["data"]] == ["temporary-assets"]


async def test_a_balance_change_invalidates_the_cached_chart():
    account = await _account(balance="0.00")

    first = body_of(await as_user("/api/v1/accounts"))
    assert first["data"][0]["money"]["amount"] == "0.00"

    await _dispatch(
        AccountUpdated(
            event_id="evt-u",
            account_id=str(account.id),
            user_external_id=EXTERNAL_USER_ID,
            user_id=account.user_id,
            previous_balance="0.00",
            new_balance="125.00",
            account_group=AccountGroup.ACCOUNT_GROUP_ASSETS,
            name=account.name,
            currency_code="USD",
            updated_at=_timestamp(),
        ),
        seq=14,
    )

    second = body_of(await as_user("/api/v1/accounts"))

    assert second["data"][0]["money"] == {"amount": "125.00", "currency": "USD"}


async def test_a_new_posting_shows_up_in_the_detail_without_an_eviction():
    """The embedded history is read live rather than cached — only the account
    ROW is cached — so a leg that lands after a first read needs nothing
    invalidated to become visible."""

    account = await _account()
    transaction = await _transaction()

    first = body_of(await as_user(f"/api/v1/accounts/{account.id}"))
    assert first["data"]["history"] == []

    await _dispatch(
        AccountPostingCreated(
            event_id="evt-p",
            posting_id=str(uuid.uuid4()),
            dispatch_id=str(uuid.uuid4()),
            account_id=str(account.id),
            transaction_id=str(transaction.id),
            user_external_id=EXTERNAL_USER_ID,
            user_id=account.user_id,
            amount="125",
            title="Groceries",
            debit=True,
            currency_code="JPY",
            position=0,
            created_at=_timestamp(),
        ),
        seq=15,
    )

    second = body_of(await as_user(f"/api/v1/accounts/{account.id}"))

    assert len(second["data"]["history"]) == 1


async def test_a_balance_change_invalidates_the_cached_detail():
    """The account row IS cached, so a restated balance has to evict it — the
    row is otherwise unreachable until the entry expires on its own."""

    account = await _account(balance="0.00")

    first = body_of(await as_user(f"/api/v1/accounts/{account.id}"))
    assert first["data"]["money"]["amount"] == "0.00"

    await _dispatch(
        AccountUpdated(
            event_id="evt-u2",
            account_id=str(account.id),
            user_external_id=EXTERNAL_USER_ID,
            user_id=account.user_id,
            previous_balance="0.00",
            new_balance="125.00",
            account_group=AccountGroup.ACCOUNT_GROUP_ASSETS,
            name=account.name,
            currency_code="USD",
            updated_at=_timestamp(),
        ),
        seq=16,
    )

    second = body_of(await as_user(f"/api/v1/accounts/{account.id}"))

    assert second["data"]["money"]["amount"] == "125.00"


async def test_an_account_event_without_a_currency_reads_as_the_book_currency():
    """A producer predating the field sends an empty string. Every account it
    could describe was booked in the default, so storing a blank would only
    make the presenter guess later."""

    await _dispatch(
        AccountCreated(
            event_id="evt-legacy",
            account_id=str(uuid.uuid4()),
            user_external_id=EXTERNAL_USER_ID,
            user_id=await _user_id(),
            account_group=AccountGroup.ACCOUNT_GROUP_EQUITY,
            name="opening-balance",
            balance="10.00",
            created_at=_timestamp(),
        ),
        seq=17,
    )

    payload = body_of(await as_user("/api/v1/accounts"))

    assert payload["data"][0]["money"] == {"amount": "10.00", "currency": "USD"}

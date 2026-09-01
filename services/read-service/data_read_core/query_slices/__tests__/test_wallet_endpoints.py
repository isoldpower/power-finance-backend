import json
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth import get_user_model
from django.test import AsyncClient

from data_read_core.shared.money import CURRENCY_CATALOG
from data_read_core.shared.postgres_orm import (
    CurrencyReadModel,
    TransactionReadModel,
    WalletReadModel,
)
from data_read_core.shared.redis_cache import get_redis
from data_read_core.shared.timestamps import Period, period_bounds

pytestmark = pytest.mark.django_db(transaction=True)

EXTERNAL_USER_ID = "user_2wallets"
AUTH_HEADERS = {"X-User-Id": EXTERNAL_USER_ID}

UTC_ZONE = ZoneInfo("UTC")
JULY = datetime(2026, 7, 15, 12, tzinfo=UTC)
AUGUST = datetime(2026, 8, 15, 12, tzinfo=UTC)


def as_user(path: str, **headers):
    return AsyncClient().get(path, headers={**AUTH_HEADERS, **headers})


def body_of(response) -> dict:
    return json.loads(response.content)


WALLET_CACHE_PREFIXES = ("read:wallets:*", "read:wallet:*", "ver:wallets:*")


@pytest.fixture(autouse=True)
async def _empty_wallet_cache():
    """Redis is not rolled back with the database, and its client is a per-loop
    singleton, so both are dropped between tests."""

    async def clear() -> None:
        get_redis.cache_clear()
        redis = get_redis()
        for pattern in WALLET_CACHE_PREFIXES:
            async for key in redis.scan_iter(match=pattern):
                await redis.delete(key)

    await clear()
    yield
    await clear()
    await get_redis().aclose()
    get_redis.cache_clear()


@pytest.fixture(autouse=True)
async def _provisioned_user_and_currencies():
    CURRENCY_CATALOG.reset()
    await get_user_model().objects.acreate(username=EXTERNAL_USER_ID)
    await CurrencyReadModel.objects.abulk_create(
        [CurrencyReadModel(code="USD", name="US Dollar", symbol="$", numeric="840", digits=2)],
        ignore_conflicts=True,
    )
    yield
    CURRENCY_CATALOG.reset()


async def _user_id() -> int:
    user = await get_user_model().objects.aget(username=EXTERNAL_USER_ID)
    return user.id


async def _wallet(
    *,
    title: str = "Main",
    balance: str = "0",
    zero_balance: str = "0",
    favorite: bool = False,
    created_at: datetime = JULY,
    deleted_at: datetime | None = None,
    category: str = "",
    color: str = "",
) -> WalletReadModel:
    return await WalletReadModel.objects.acreate(
        id=uuid.uuid4(),
        user_id=await _user_id(),
        title=title,
        currency_code="USD",
        balance=Decimal(balance),
        zero_balance=Decimal(zero_balance),
        favorite=favorite,
        category=category,
        color=color,
        created_at=created_at,
        deleted_at=deleted_at,
    )


async def test_preview_carries_the_target_shape():
    wallet = await _wallet(
        title="Random Credit Card",
        balance="50.00",
        zero_balance="100.00",
        favorite=True,
        category="Savings",
        color="#FF0000",
    )

    response = await as_user("/api/v1/wallets")

    assert response.status_code == 200
    assert body_of(response)["data"] == [
        {
            "id": str(wallet.id),
            "name": "Random Credit Card",
            "created_at": "2026-07-15T12:00:00+00:00",
            "updated_at": None,
            "deleted_at": None,
            "category": "Savings",
            "currency": "USD",
            "money": {"amount": "50.00", "currency": "USD"},
            "zero_balance": {"amount": "100.00", "currency": "USD"},
            "favorite": True,
            "color": "#FF0000",
        }
    ]


async def test_favorites_lead_regardless_of_age():
    """`favorite DESC` is the leading key, so an old favourite outranks a new
    ordinary wallet."""

    await _wallet(title="New ordinary", created_at=datetime(2026, 8, 1, tzinfo=UTC))
    await _wallet(title="Old favourite", favorite=True, created_at=datetime(2026, 1, 1, tzinfo=UTC))

    response = await as_user("/api/v1/wallets")

    assert [row["name"] for row in body_of(response)["data"]] == [
        "Old favourite",
        "New ordinary",
    ]


async def test_closed_wallets_leave_the_list():
    await _wallet(title="Open")
    await _wallet(title="Closed", deleted_at=AUGUST)

    response = await as_user("/api/v1/wallets")

    payload = body_of(response)
    assert [row["name"] for row in payload["data"]] == ["Open"]
    assert payload["meta"]["total"] == 1


async def test_a_closed_wallet_still_resolves_by_id():
    """DELETE removes a wallet from lists and search, not from existence."""

    wallet = await _wallet(title="Closed", deleted_at=AUGUST)

    response = await as_user(f"/api/v1/wallets/{wallet.id}")

    assert response.status_code == 200
    assert body_of(response)["data"]["deleted_at"] == "2026-08-15T12:00:00+00:00"


async def test_detail_reports_period_flows_as_positive_magnitudes():
    """Dates are derived from the window rather than written down.

    `last_month` is resolved against the wall clock, and the endpoint gives a
    test no way to pin it — so fixed dates only sit inside the window during the
    month they were written in, and the test starts failing on its own the
    moment the calendar moves past it. `period_bounds` is unit-tested against a
    pinned `now` elsewhere; what this test is for is that the ENDPOINT filters
    to whatever that window is and reports both directions as positive.
    """

    since, until = period_bounds(Period.LAST_MONTH, UTC_ZONE)
    wallet = await _wallet(balance="30.00")
    user_id = await _user_id()
    for amount, occurred_at in (
        (Decimal("50.00"), since + timedelta(days=9)),
        (Decimal("-20.00"), since + timedelta(days=19)),
        # Decoys either side of the window. `until` is the first instant of the
        # CURRENT period, so it is outside `last_month` by one instant.
        (Decimal("999.00"), until),
        (Decimal("777.00"), since - timedelta(days=1)),
    ):
        await TransactionReadModel.objects.acreate(
            id=uuid.uuid4(),
            wallet_id=wallet.id,
            user_id=user_id,
            amount=amount,
            currency_code="USD",
            occurred_at=occurred_at,
            created_at=occurred_at,
        )

    response = await as_user(
        f"/api/v1/wallets/{wallet.id}",
        **{"X-User-Timezone": "UTC"},
    )

    assert body_of(response)["data"]["period"] == {
        "inflow": {"amount": "50.00", "currency": "USD"},
        "outflow": {"amount": "20.00", "currency": "USD"},
    }


async def test_period_is_zeroed_rather_than_absent_when_nothing_moved():
    wallet = await _wallet()

    response = await as_user(f"/api/v1/wallets/{wallet.id}")

    assert body_of(response)["data"]["period"] == {
        "inflow": {"amount": "0.00", "currency": "USD"},
        "outflow": {"amount": "0.00", "currency": "USD"},
    }


async def test_the_window_defaults_to_last_month_and_is_echoed():
    wallet = await _wallet()

    payload = body_of(await as_user(f"/api/v1/wallets/{wallet.id}"))

    assert payload["meta"]["period"] == "last_month"


async def test_a_wider_period_picks_up_what_last_month_excludes():
    """The transaction sits outside last month but inside last year, so the
    same wallet reports different figures for the two windows."""

    wallet = await _wallet()
    user_id = await _user_id()
    await TransactionReadModel.objects.acreate(
        id=uuid.uuid4(),
        wallet_id=wallet.id,
        user_id=user_id,
        amount=Decimal("500.00"),
        currency_code="USD",
        occurred_at=datetime(2025, 3, 10, tzinfo=UTC),
        created_at=datetime(2025, 3, 10, tzinfo=UTC),
    )

    last_month = body_of(await as_user(f"/api/v1/wallets/{wallet.id}?period=last_month"))
    all_time = body_of(await as_user(f"/api/v1/wallets/{wallet.id}?period=all_time"))

    assert last_month["data"]["period"]["inflow"]["amount"] == "0.00"
    assert all_time["data"]["period"]["inflow"]["amount"] == "500.00"
    assert all_time["meta"]["period"] == "all_time"


async def test_all_time_has_no_boundaries_at_all():
    """Every other window is a calendar range; `all_time` drops both bounds
    rather than reaching for an arbitrary epoch."""

    wallet = await _wallet()
    user_id = await _user_id()
    for occurred_at in (datetime(2019, 1, 1, tzinfo=UTC), datetime(2031, 1, 1, tzinfo=UTC)):
        await TransactionReadModel.objects.acreate(
            id=uuid.uuid4(),
            wallet_id=wallet.id,
            user_id=user_id,
            amount=Decimal("10.00"),
            currency_code="USD",
            occurred_at=occurred_at,
            created_at=occurred_at,
        )

    payload = body_of(await as_user(f"/api/v1/wallets/{wallet.id}?period=all_time"))

    assert payload["data"]["period"]["inflow"]["amount"] == "20.00"


async def test_an_unknown_period_is_refused_rather_than_quietly_defaulted():
    """Answering about a different window than the one asked for would be worse
    than refusing."""

    wallet = await _wallet()

    response = await as_user(f"/api/v1/wallets/{wallet.id}?period=last_fortnight")

    assert response.status_code == 422
    error = body_of(response)["error"]
    assert error["code"] == "validation_failed"
    assert error["details"][0]["field"] == "period"


async def test_another_users_wallet_is_not_an_existence_oracle():
    stranger = await get_user_model().objects.acreate(username="user_someone_else")
    foreign = await WalletReadModel.objects.acreate(
        id=uuid.uuid4(),
        user_id=stranger.id,
        title="Theirs",
        currency_code="USD",
        balance=Decimal("0"),
        created_at=JULY,
    )

    response = await as_user(f"/api/v1/wallets/{foreign.id}")

    assert response.status_code == 404


async def _recent_transaction(
    wallet: WalletReadModel,
    *,
    name: str,
    amount: str = "-10.00",
    created_at: datetime = JULY,
    deleted_at: datetime | None = None,
) -> TransactionReadModel:
    return await TransactionReadModel.objects.acreate(
        id=uuid.uuid4(),
        wallet_id=wallet.id,
        wallet_name=wallet.title,
        user_id=await _user_id(),
        amount=Decimal(amount),
        currency_code="USD",
        name=name,
        category="Some Category",
        origin="manual",
        occurred_at=created_at,
        created_at=created_at,
        deleted_at=deleted_at,
    )


async def test_detail_embeds_recent_transactions_in_the_preview_shape():
    wallet = await _wallet()
    await _recent_transaction(wallet, name="Groceries store")

    payload = body_of(await as_user(f"/api/v1/wallets/{wallet.id}"))

    assert payload["data"]["recent"] == [
        {
            "id": payload["data"]["recent"][0]["id"],
            "name": "Groceries store",
            "created_at": "2026-07-15T12:00:00+00:00",
            "updated_at": None,
            "deleted_at": None,
            "money": {"amount": "10.00", "currency": "USD"},
            "type": "expense",
            "origin": "manual",
            "wallet": {"id": str(wallet.id), "name": "Main"},
            "category": "Some Category",
            "chain_id": None,
        }
    ]


async def test_recent_is_paginated_under_its_own_meta_namespace():
    wallet = await _wallet()
    for index in range(3):
        await _recent_transaction(
            wallet,
            name=f"Transaction {index}",
            created_at=datetime(2026, 7, 10 + index, tzinfo=UTC),
        )

    payload = body_of(await as_user(f"/api/v1/wallets/{wallet.id}?limit=2"))

    assert [row["name"] for row in payload["data"]["recent"]] == [
        "Transaction 2",
        "Transaction 1",
    ]
    assert payload["meta"]["recent"]["limit"] == 2
    assert payload["meta"]["recent"]["total"] == 3
    assert payload["meta"]["recent"]["next_cursor"] is not None
    assert payload["meta"]["recent"]["prev_cursor"] is None


async def test_the_recent_cursor_walks_to_the_next_page():
    wallet = await _wallet()
    for index in range(3):
        await _recent_transaction(
            wallet,
            name=f"Transaction {index}",
            created_at=datetime(2026, 7, 10 + index, tzinfo=UTC),
        )

    first = body_of(await as_user(f"/api/v1/wallets/{wallet.id}?limit=2"))
    cursor = first["meta"]["recent"]["next_cursor"]
    second = body_of(await as_user(f"/api/v1/wallets/{wallet.id}?limit=2&cursor={cursor}"))

    assert [row["name"] for row in second["data"]["recent"]] == ["Transaction 0"]


async def test_recent_excludes_cancelled_transactions():
    wallet = await _wallet()
    await _recent_transaction(wallet, name="Live")
    await _recent_transaction(wallet, name="Cancelled", deleted_at=AUGUST)

    payload = body_of(await as_user(f"/api/v1/wallets/{wallet.id}"))

    assert [row["name"] for row in payload["data"]["recent"]] == ["Live"]
    assert payload["meta"]["recent"]["total"] == 1


async def test_recent_only_carries_this_wallets_transactions():
    wallet = await _wallet(title="Mine")
    other = await _wallet(title="Other")
    await _recent_transaction(wallet, name="Mine")
    await _recent_transaction(other, name="Theirs")

    payload = body_of(await as_user(f"/api/v1/wallets/{wallet.id}"))

    assert [row["name"] for row in payload["data"]["recent"]] == ["Mine"]


async def test_recent_is_empty_rather_than_absent_on_a_fresh_wallet():
    wallet = await _wallet()

    payload = body_of(await as_user(f"/api/v1/wallets/{wallet.id}"))

    assert payload["data"]["recent"] == []
    assert payload["meta"]["recent"]["total"] == 0

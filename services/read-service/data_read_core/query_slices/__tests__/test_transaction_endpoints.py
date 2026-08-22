import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import AsyncClient

from data_read_core.shared.money import CURRENCY_CATALOG
from data_read_core.shared.postgres_orm import (
    NO_CHAIN_SENTINEL,
    CurrencyReadModel,
    TransactionReadModel,
    WalletReadModel,
)
from data_read_core.shared.redis_cache import get_redis

pytestmark = pytest.mark.django_db(transaction=True)

EXTERNAL_USER_ID = "user_2txns"
AUTH_HEADERS = {"X-User-Id": EXTERNAL_USER_ID}
WALLET_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
CACHE_PREFIXES = ("read:transactions:*", "read:transaction:*", "ver:transactions:*")


def as_user(path: str):
    return AsyncClient().get(path, headers=AUTH_HEADERS)


def body_of(response) -> dict:
    return json.loads(response.content)


@pytest.fixture(autouse=True)
async def _empty_cache():
    """`transaction=True` resets sequences, so consecutive tests can reuse a
    user id — and with it a cached page from the test before."""

    async def clear() -> None:
        get_redis.cache_clear()
        redis = get_redis()
        for pattern in CACHE_PREFIXES:
            async for key in redis.scan_iter(match=pattern):
                await redis.delete(key)

    await clear()
    yield
    await clear()
    await get_redis().aclose()
    get_redis.cache_clear()


@pytest.fixture(autouse=True)
async def _provisioned():
    CURRENCY_CATALOG.reset()
    user = await get_user_model().objects.acreate(username=EXTERNAL_USER_ID)
    await CurrencyReadModel.objects.abulk_create(
        [CurrencyReadModel(code="USD", name="US Dollar", symbol="$", numeric="840", digits=2)],
        ignore_conflicts=True,
    )
    await WalletReadModel.objects.acreate(
        id=WALLET_ID,
        user_id=user.id,
        title="Random Credit Card",
        currency_code="USD",
        balance=Decimal("0"),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    yield
    CURRENCY_CATALOG.reset()


async def _user_id() -> int:
    user = await get_user_model().objects.aget(username=EXTERNAL_USER_ID)
    return user.id


async def _transaction(
    *,
    amount: str = "-50.00",
    name: str = "Groceries store",
    category: str | None = "Some Category",
    origin: str = "manual",
    chain_id: uuid.UUID | None = None,
    created_at: datetime = datetime(2026, 8, 12, 11, 51, tzinfo=UTC),
    deleted_at: datetime | None = None,
) -> TransactionReadModel:
    return await TransactionReadModel.objects.acreate(
        id=uuid.uuid4(),
        wallet_id=WALLET_ID,
        wallet_name="Random Credit Card",
        user_id=await _user_id(),
        amount=Decimal(amount),
        currency_code="USD",
        name=name,
        category=category,
        origin=origin,
        chain_id=chain_id,
        chain_sort=chain_id or NO_CHAIN_SENTINEL,
        occurred_at=created_at,
        created_at=created_at,
        deleted_at=deleted_at,
    )


async def test_preview_carries_the_target_shape():
    transaction = await _transaction()

    response = await as_user("/api/v1/transactions")

    assert response.status_code == 200
    assert body_of(response)["data"] == [
        {
            "id": str(transaction.id),
            "name": "Groceries store",
            "created_at": "2026-08-12T11:51:00+00:00",
            "updated_at": None,
            "deleted_at": None,
            "money": {"amount": "50.00", "currency": "USD"},
            "type": "expense",
            "origin": "manual",
            "wallet": {"id": str(WALLET_ID), "name": "Random Credit Card"},
            "category": "Some Category",
            "chain_id": None,
        }
    ]


async def test_money_is_a_positive_magnitude_and_direction_is_the_type():
    """The sign never reaches the wire — `type` carries it, so the two cannot
    contradict each other."""

    await _transaction(amount="-50.00", name="Spent")
    await _transaction(amount="90.00", name="Earned")

    rows = {row["name"]: row for row in body_of(await as_user("/api/v1/transactions"))["data"]}

    assert rows["Spent"]["money"]["amount"] == "50.00"
    assert rows["Spent"]["type"] == "expense"
    assert rows["Earned"]["money"]["amount"] == "90.00"
    assert rows["Earned"]["type"] == "income"


async def test_cancelled_transactions_leave_the_feed():
    await _transaction(name="Live")
    await _transaction(name="Cancelled", deleted_at=datetime(2026, 8, 13, tzinfo=UTC))

    payload = body_of(await as_user("/api/v1/transactions"))

    assert [row["name"] for row in payload["data"]] == ["Live"]
    assert payload["meta"]["total"] == 1


async def test_chain_members_arrive_contiguously():
    """Chain legs share a commit timestamp, so ordering by chain keeps a transfer
    together instead of interleaved with unrelated transactions."""

    same_instant = datetime(2026, 8, 12, 11, 51, tzinfo=UTC)
    chain = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
    await _transaction(name="Unrelated", created_at=same_instant)
    await _transaction(name="Leg one", created_at=same_instant, chain_id=chain)
    await _transaction(name="Leg two", created_at=same_instant, chain_id=chain)

    names = [row["name"] for row in body_of(await as_user("/api/v1/transactions"))["data"]]
    legs = [index for index, name in enumerate(names) if name.startswith("Leg")]

    assert legs == [legs[0], legs[0] + 1]


async def test_a_standalone_transaction_sorts_after_chained_ones():
    """`chain_id ASC NULLS LAST` — the sentinel is what makes the null sort
    last through a keyset cursor."""

    same_instant = datetime(2026, 8, 12, 11, 51, tzinfo=UTC)
    chain = uuid.UUID("00000000-0000-0000-0000-00000000000a")
    await _transaction(name="Standalone", created_at=same_instant)
    await _transaction(name="Chained", created_at=same_instant, chain_id=chain)

    names = [row["name"] for row in body_of(await as_user("/api/v1/transactions"))["data"]]

    assert names == ["Chained", "Standalone"]


async def test_paging_through_the_feed_reaches_every_row():
    for index in range(3):
        await _transaction(
            name=f"Transaction {index}",
            created_at=datetime(2026, 8, 12, 11, 51 + index, tzinfo=UTC),
        )

    seen: list[str] = []
    path = "/api/v1/transactions?limit=1"
    for _ in range(3):
        response = await as_user(path)
        payload = body_of(response)
        assert response.status_code == 200, payload
        seen.extend(row["name"] for row in payload["data"])
        cursor = payload["meta"]["next_cursor"]
        if cursor is None:
            break
        path = f"/api/v1/transactions?limit=1&cursor={cursor}"

    assert seen == ["Transaction 2", "Transaction 1", "Transaction 0"]


async def test_detail_adds_evidence_and_the_empty_posting_set():
    transaction = await _transaction()

    payload = body_of(await as_user(f"/api/v1/transactions/{transaction.id}"))

    assert payload["data"]["evidence"] is None
    assert payload["data"]["postings"] == []
    assert payload["data"]["analysis"] is None


async def test_a_cancelled_transaction_still_resolves_by_id():
    transaction = await _transaction(deleted_at=datetime(2026, 8, 13, tzinfo=UTC))

    response = await as_user(f"/api/v1/transactions/{transaction.id}")

    assert response.status_code == 200
    assert body_of(response)["data"]["deleted_at"] == "2026-08-13T00:00:00+00:00"
    assert body_of(response)["data"]["money"]["amount"] == "50.00"

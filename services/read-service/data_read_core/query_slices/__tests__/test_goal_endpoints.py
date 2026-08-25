import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import AsyncClient

from data_read_core.shared.money import CURRENCY_CATALOG
from data_read_core.shared.postgres_orm import (
    CurrencyReadModel,
    GoalReadModel,
    MoneyContainers,
    TransactionReadModel,
    WalletReadModel,
)
from data_read_core.shared.redis_cache import get_redis

pytestmark = pytest.mark.django_db(transaction=True)

EXTERNAL_USER_ID = "user_2goals"
AUTH_HEADERS = {"X-User-Id": EXTERNAL_USER_ID}

JULY = datetime(2026, 7, 15, 12, tzinfo=UTC)
AUGUST = datetime(2026, 8, 15, 12, tzinfo=UTC)

GOAL_CACHE_PREFIXES = ("read:goals:*", "read:goal:*", "ver:goals:*")


def as_user(path: str, **headers):
    return AsyncClient().get(path, headers={**AUTH_HEADERS, **headers})


def body_of(response) -> dict:
    return json.loads(response.content)


@pytest.fixture(autouse=True)
async def _empty_goal_cache():
    async def clear() -> None:
        get_redis.cache_clear()
        redis = get_redis()
        for pattern in GOAL_CACHE_PREFIXES:
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


async def _goal(
    *,
    title: str = "New bike",
    target: str = "500.00",
    progress: str = "0",
    created_at: datetime = JULY,
    finish_at: datetime | None = None,
    deleted_at: datetime | None = None,
) -> GoalReadModel:
    return await GoalReadModel.objects.acreate(
        id=uuid.uuid4(),
        user_id=await _user_id(),
        title=title,
        currency_code="USD",
        target=Decimal(target),
        progress=Decimal(progress),
        finish_at=finish_at,
        created_at=created_at,
        deleted_at=deleted_at,
    )


async def _transaction(
    container_id,
    *,
    amount: str,
    name: str = "Goal Savings",
    kind: str = MoneyContainers.GOAL,
    created_at: datetime = AUGUST,
    deleted_at: datetime | None = None,
) -> TransactionReadModel:
    return await TransactionReadModel.objects.acreate(
        id=uuid.uuid4(),
        wallet_id=container_id,
        wallet_name="New bike",
        container_kind=kind,
        user_id=await _user_id(),
        amount=Decimal(amount),
        currency_code="USD",
        name=name,
        occurred_at=created_at,
        created_at=created_at,
        deleted_at=deleted_at,
    )


async def test_listing_returns_goals_newest_first():
    older = await _goal(title="Older", created_at=JULY)
    newer = await _goal(title="Newer", created_at=AUGUST)

    body = body_of(await as_user("/api/v1/goals"))

    assert [row["name"] for row in body["data"]] == ["Newer", "Older"]
    assert [row["id"] for row in body["data"]] == [str(newer.id), str(older.id)]


async def test_a_nearer_deadline_does_not_move_a_goal_up_the_list():
    """Ordering is `created_at DESC` and nothing else. The target is explicit that
    a goal does not move because its deadline approaches."""

    await _goal(
        title="Distant deadline", created_at=AUGUST, finish_at=datetime(2027, 1, 1, tzinfo=UTC)
    )
    await _goal(
        title="Imminent deadline", created_at=JULY, finish_at=datetime(2026, 9, 1, tzinfo=UTC)
    )

    body = body_of(await as_user("/api/v1/goals"))

    assert [row["name"] for row in body["data"]] == ["Distant deadline", "Imminent deadline"]


async def test_closed_goals_leave_the_listing():
    await _goal(title="Open")
    await _goal(title="Closed", deleted_at=AUGUST)

    body = body_of(await as_user("/api/v1/goals"))

    assert [row["name"] for row in body["data"]] == ["Open"]
    assert body["meta"]["total"] == 1


async def test_money_is_reported_at_the_currency_scale():
    goal = await _goal(target="500", progress="30")

    body = body_of(await as_user(f"/api/v1/goals/{goal.id}"))

    assert body["data"]["target"] == {"amount": "500.00", "currency": "USD"}
    assert body["data"]["progress"] == {"amount": "30.00", "currency": "USD"}


async def test_a_closed_goal_still_resolves_by_id():
    """DELETE removes a goal from lists, not from existence — the transactions that
    funded it still have to render a name."""

    goal = await _goal(title="Closed", deleted_at=AUGUST)

    response = await as_user(f"/api/v1/goals/{goal.id}")

    assert response.status_code == 200
    assert body_of(response)["data"]["deleted_at"] is not None


async def test_another_users_goal_is_a_404_not_a_403():
    other_user = await get_user_model().objects.acreate(username="user_someone_else")
    stranger_goal = await GoalReadModel.objects.acreate(
        id=uuid.uuid4(),
        user_id=other_user.id,
        title="Not yours",
        currency_code="USD",
        target=Decimal("10"),
        created_at=JULY,
    )

    response = await as_user(f"/api/v1/goals/{stranger_goal.id}")

    assert response.status_code == 404


async def test_history_carries_the_goals_transactions():
    goal = await _goal()
    await _transaction(goal.id, amount="30.00", name="Goal Savings")

    body = body_of(await as_user(f"/api/v1/goals/{goal.id}"))
    entry = body["data"]["history"][0]

    assert entry["title"] == "Goal Savings"
    assert entry["debit"] is True
    assert entry["money"] == {"amount": "30.00", "currency": "USD"}
    assert entry["source_transaction"] == entry["id"]


async def test_money_leaving_the_goal_is_a_credit():
    goal = await _goal()
    await _transaction(goal.id, amount="-30.00", name="Spent on the bike")

    body = body_of(await as_user(f"/api/v1/goals/{goal.id}"))
    entry = body["data"]["history"][0]

    assert entry["debit"] is False
    assert entry["money"]["amount"] == "30.00", "history reports a magnitude, direction is `debit`"


async def test_history_ignores_a_wallet_that_shares_the_id():
    """`wallet_id` holds a container id of either kind, so the history query has to
    filter on the kind as well or it would inherit a wallet's transactions."""

    goal = await _goal()
    await _transaction(goal.id, amount="30.00", name="Into the goal")
    await _transaction(goal.id, amount="99.00", name="Into a wallet", kind=MoneyContainers.WALLET)

    body = body_of(await as_user(f"/api/v1/goals/{goal.id}"))

    assert [entry["title"] for entry in body["data"]["history"]] == ["Into the goal"]
    assert body["meta"]["history"]["total"] == 1


async def test_history_excludes_cancelled_transactions():
    goal = await _goal()
    await _transaction(goal.id, amount="30.00", name="Live")
    await _transaction(goal.id, amount="10.00", name="Cancelled", deleted_at=AUGUST)

    body = body_of(await as_user(f"/api/v1/goals/{goal.id}"))

    assert [entry["title"] for entry in body["data"]["history"]] == ["Live"]


async def test_history_paginates_under_its_own_meta_namespace():
    goal = await _goal()
    for index in range(3):
        await _transaction(
            goal.id,
            amount="10.00",
            name=f"Entry {index}",
            created_at=datetime(2026, 8, index + 1, tzinfo=UTC),
        )

    body = body_of(await as_user(f"/api/v1/goals/{goal.id}?limit=2"))

    assert len(body["data"]["history"]) == 2
    assert body["meta"]["history"]["total"] == 3
    assert body["meta"]["history"]["next_cursor"] is not None


async def test_the_history_cursor_round_trips():
    goal = await _goal()
    for index in range(3):
        await _transaction(
            goal.id,
            amount="10.00",
            name=f"Entry {index}",
            created_at=datetime(2026, 8, index + 1, tzinfo=UTC),
        )

    first = body_of(await as_user(f"/api/v1/goals/{goal.id}?limit=2"))
    cursor = first["meta"]["history"]["next_cursor"]
    second = body_of(await as_user(f"/api/v1/goals/{goal.id}?limit=2&cursor={cursor}"))

    seen = [entry["title"] for entry in first["data"]["history"]]
    seen += [entry["title"] for entry in second["data"]["history"]]
    assert sorted(seen) == ["Entry 0", "Entry 1", "Entry 2"]


async def test_goals_are_not_wallets():
    """The two live in separate collections. A goal must not surface under
    /wallets, whatever it shares structurally."""

    goal = await _goal(title="New bike")
    await WalletReadModel.objects.acreate(
        id=uuid.uuid4(),
        user_id=await _user_id(),
        title="Main",
        currency_code="USD",
        balance=Decimal("0"),
        created_at=JULY,
    )

    wallets = body_of(await as_user("/api/v1/wallets"))

    assert [row["name"] for row in wallets["data"]] == ["Main"]
    assert str(goal.id) not in [row["id"] for row in wallets["data"]]

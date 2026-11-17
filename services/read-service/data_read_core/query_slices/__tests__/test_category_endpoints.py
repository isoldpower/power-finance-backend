import json
from datetime import UTC, datetime

import pytest
from django.contrib.auth import get_user_model
from django.test import AsyncClient

from data_read_core.shared.postgres_orm import CategoryReadModel
from data_read_core.shared.redis_cache import get_redis

from .category_fixtures import global_category, owned_category

pytestmark = pytest.mark.django_db(transaction=True)

EXTERNAL_USER_ID = "user_categories"
OTHER_USER_ID = "user_other_categories"
AUTH_HEADERS = {"X-User-Id": EXTERNAL_USER_ID}


def body_of(response) -> dict:
    return json.loads(response.content)


@pytest.fixture(autouse=True)
async def _empty_cache():
    async def clear() -> None:
        get_redis.cache_clear()
        redis = get_redis()
        for pattern in ("read:categories:*", "ver:categories:*"):
            async for key in redis.scan_iter(match=pattern):
                await redis.delete(key)

    await clear()
    yield
    await clear()
    await get_redis().aclose()
    get_redis.cache_clear()


@pytest.fixture
async def owner_id() -> int:
    owner = await get_user_model().objects.acreate(username=EXTERNAL_USER_ID)
    await get_user_model().objects.acreate(username=OTHER_USER_ID)
    return owner.id


async def _list(**parameters):
    query_string = "&".join(f"{key}={value}" for key, value in parameters.items())
    return await AsyncClient().get(f"/api/v1/categories?{query_string}", headers=AUTH_HEADERS)


async def test_globals_come_first_then_own_categories_alphabetically(owner_id):
    await global_category("transaction", "Food")
    await global_category("transaction", "Dining")
    await owned_category(owner_id, "transaction", "Zoo")
    await owned_category(owner_id, "transaction", "Aquarium")

    payload = body_of(await _list(kind="transaction"))
    names = [category["name"] for category in payload["data"]]
    global_names = [category["name"] for category in payload["data"] if category["is_global"]]

    assert names[-2:] == ["Aquarium", "Zoo"]
    assert global_names == sorted(global_names)
    assert {"Dining", "Food"} <= set(global_names)
    assert payload["meta"]["total"] == len(names)


async def test_deleted_and_foreign_categories_are_left_out(owner_id):
    retired = await owned_category(owner_id, "transaction", "Retired")
    retired.deleted_at = datetime(2026, 11, 1, tzinfo=UTC)
    await retired.asave()
    stranger = await get_user_model().objects.aget(username=OTHER_USER_ID)
    await owned_category(stranger.id, "transaction", "Theirs")

    names = [category["name"] for category in body_of(await _list())["data"]]

    assert "Retired" not in names
    assert "Theirs" not in names


async def test_the_kind_filter_keeps_one_kind(owner_id):
    await owned_category(owner_id, "wallet", "Side account")
    await owned_category(owner_id, "transaction", "Pets")

    payload = body_of(await _list(kind="wallet"))

    assert {category["kind"] for category in payload["data"]} == {"wallet"}
    assert "Side account" in [category["name"] for category in payload["data"]]


async def test_an_unknown_kind_is_refused(owner_id):
    response = await _list(kind="goal")

    assert response.status_code == 422


async def test_a_category_carries_its_full_shape(owner_id):
    pets = await owned_category(owner_id, "transaction", "Pets")
    await CategoryReadModel.objects.filter(is_global=True).adelete()

    payload = body_of(await _list(kind="transaction"))

    assert payload["data"] == [
        {
            "id": str(pets.id),
            "kind": "transaction",
            "name": "Pets",
            "is_global": False,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": None,
            "deleted_at": None,
        }
    ]

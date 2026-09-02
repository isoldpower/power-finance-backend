"""Reading webhook endpoints, their subscriptions and the event catalog.

The delivery log is deliberately absent here: it lives in webhook-service's own
Postgres and the gateway routes that one read there.
"""

import json
import uuid
from datetime import UTC, datetime

import pytest
from django.contrib.auth import get_user_model
from django.test import AsyncClient
from webhook_catalog_py import event_types

from data_read_core.shared.postgres_orm import (
    WebhookReadModel,
    WebhookSubscriptionReadModel,
)
from data_read_core.shared.redis_cache import get_redis

pytestmark = pytest.mark.django_db(transaction=True)

EXTERNAL_USER_ID = "user_webhooks"
OTHER_USER_ID = "user_other_webhooks"
AUTH_HEADERS = {"X-User-Id": EXTERNAL_USER_ID}
WEBHOOKS = "/api/v1/webhooks"

JANUARY = datetime(2026, 1, 10, tzinfo=UTC)
FEBRUARY = datetime(2026, 2, 10, tzinfo=UTC)

CACHE_PREFIXES = ("read:webhooks:*", "ver:webhooks:*", "read:webhook_events:*")


def as_user(path: str):
    return AsyncClient().get(path, headers=AUTH_HEADERS)


def body_of(response) -> dict:
    return json.loads(response.content)


@pytest.fixture(autouse=True)
async def _empty_cache():
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
    await get_user_model().objects.acreate(username=EXTERNAL_USER_ID)
    await get_user_model().objects.acreate(username=OTHER_USER_ID)


async def _user_id(username: str = EXTERNAL_USER_ID) -> int:
    user = await get_user_model().objects.aget(username=username)
    return user.id


async def _webhook(
    *,
    title: str = "Ledger sync",
    url: str = "https://hooks.example.com/finance/ledger",
    is_active: bool = True,
    created_at: datetime = FEBRUARY,
    owner: str = EXTERNAL_USER_ID,
) -> WebhookReadModel:
    return await WebhookReadModel.objects.acreate(
        id=uuid.uuid4(),
        user_id=await _user_id(owner),
        title=title,
        url=url,
        is_active=is_active,
        created_at=created_at,
        updated_at=None,
    )


async def _subscription(webhook: WebhookReadModel, event_type: str) -> WebhookSubscriptionReadModel:
    return await WebhookSubscriptionReadModel.objects.acreate(
        id=uuid.uuid4(),
        webhook=webhook,
        user_id=webhook.user_id,
        event_type=event_type,
        created_at=FEBRUARY,
    )


# --- endpoint shape ---------------------------------------------------------


async def test_an_endpoint_reports_enabled_and_never_its_secret():
    await _webhook()

    row = body_of(await as_user(WEBHOOKS))["data"][0]

    assert row["title"] == "Ledger sync"
    assert row["url"] == "https://hooks.example.com/finance/ledger"
    assert row["enabled"] is True
    assert "secret" not in row
    assert "is_active" not in row


async def test_an_endpoint_has_no_deleted_at():
    """Webhooks are HARD deleted, unlike every other resource in this API."""

    await _webhook()

    assert "deleted_at" not in body_of(await as_user(WEBHOOKS))["data"][0]


async def test_a_detail_read_matches_one_row_of_the_list():
    webhook = await _webhook()

    listed = body_of(await as_user(WEBHOOKS))["data"][0]
    detail = body_of(await as_user(f"{WEBHOOKS}/{webhook.id}"))["data"]

    assert detail == listed


async def test_another_users_endpoint_is_not_found():
    webhook = await _webhook(owner=OTHER_USER_ID)

    assert (await as_user(f"{WEBHOOKS}/{webhook.id}")).status_code == 404


# --- the enabled filter -----------------------------------------------------


async def test_absent_enabled_returns_both():
    await _webhook(title="live", is_active=True)
    await _webhook(title="paused", is_active=False, created_at=JANUARY)

    titles = [row["title"] for row in body_of(await as_user(WEBHOOKS))["data"]]

    assert sorted(titles) == ["live", "paused"]


@pytest.mark.parametrize(
    ("query", "expected"),
    [("enabled=true", "live"), ("enabled=false", "paused")],
)
async def test_enabled_restricts_to_one_side(query, expected):
    await _webhook(title="live", is_active=True)
    await _webhook(title="paused", is_active=False, created_at=JANUARY)

    rows = body_of(await as_user(f"{WEBHOOKS}?{query}"))["data"]

    assert [row["title"] for row in rows] == [expected]


async def test_a_non_boolean_enabled_is_refused():
    response = await as_user(f"{WEBHOOKS}?enabled=maybe")

    assert response.status_code == 422
    assert body_of(response)["error"]["details"][0]["field"] == "enabled"


async def test_the_filter_does_not_leak_across_cached_pages():
    """The filter is part of the cache key, or a filtered page would be served
    from an unfiltered one."""

    await _webhook(title="live", is_active=True)
    await _webhook(title="paused", is_active=False, created_at=JANUARY)

    await as_user(WEBHOOKS)
    rows = body_of(await as_user(f"{WEBHOOKS}?enabled=true"))["data"]

    assert [row["title"] for row in rows] == ["live"]


# --- subscriptions ----------------------------------------------------------


async def test_a_subscription_is_its_own_resource_named_by_event():
    webhook = await _webhook()
    subscription = await _subscription(webhook, "transaction.created")

    row = body_of(await as_user(f"{WEBHOOKS}/{webhook.id}/events"))["data"][0]

    assert row["id"] == str(subscription.id)
    assert row["webhook_id"] == str(webhook.id)
    assert row["event"] == "transaction.created"
    assert set(row) == {"id", "webhook_id", "event", "created_at"}


async def test_subscriptions_of_another_users_endpoint_are_not_found():
    webhook = await _webhook(owner=OTHER_USER_ID)

    assert (await as_user(f"{WEBHOOKS}/{webhook.id}/events")).status_code == 404


# --- the event catalog ------------------------------------------------------


async def test_the_catalog_serves_the_shared_table():
    body = body_of(await as_user(f"{WEBHOOKS}/event-types"))

    assert body["data"] == [
        {"event": entry.event, "subject": entry.subject, "description": entry.description}
        for entry in event_types()
    ]


async def test_the_catalog_is_not_paginated():
    """It is small, fixed at any given moment and always returned complete."""

    meta = body_of(await as_user(f"{WEBHOOKS}/event-types"))["meta"]

    assert meta == {
        "limit": None,
        "total": len(event_types()),
        "next_cursor": None,
        "prev_cursor": None,
    }


async def test_the_catalog_never_leaks_the_publisher_mapping():
    """`outbox_types` is how the publisher routes an event, not something a
    subscriber can act on."""

    for row in body_of(await as_user(f"{WEBHOOKS}/event-types"))["data"]:
        assert set(row) == {"event", "subject", "description"}


# --- search --------------------------------------------------------------


async def test_search_filters_on_enabled_not_the_stored_column():
    """`is_active` is storage; the API's name for the pause switch is
    `enabled`, and that is what a filter tree must spell."""

    await _webhook(title="live", is_active=True)
    await _webhook(title="paused", is_active=False, created_at=JANUARY)

    response = await AsyncClient().post(
        f"{WEBHOOKS}/search",
        data=json.dumps(
            {"filter_body": {"field_name": "enabled", "operator": "eq", "value": True}}
        ),
        content_type="application/json",
        headers=AUTH_HEADERS,
    )

    assert [row["title"] for row in body_of(response)["data"]] == ["live"]


async def test_search_refuses_the_stored_column_name():
    response = await AsyncClient().post(
        f"{WEBHOOKS}/search",
        data=json.dumps(
            {"filter_body": {"field_name": "is_active", "operator": "eq", "value": True}}
        ),
        content_type="application/json",
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422

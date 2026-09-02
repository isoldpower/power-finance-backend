"""Reading user-authored rules.

The list returns the COMPLETE resource rather than a preview: a rule is small
and its condition renders inline, so a detail request would fetch nothing new.
"""

import json
import uuid
from datetime import UTC, datetime

import pytest
from background_workers.services.build_event_router import _subscribe_all_events
from django.contrib.auth import get_user_model
from django.test import AsyncClient
from fakes import make_event
from google.protobuf.timestamp_pb2 import Timestamp
from kafka_consumer_py import KafkaEventRouter
from kafka_messages import (
    AutomationCreated,
    AutomationDeleted,
    AutomationEffect,
    AutomationRan,
    AutomationTrigger,
    AutomationUpdated,
)

from data_read_core.shared.postgres_orm import AutomationReadModel
from data_read_core.shared.redis_cache import get_redis

pytestmark = pytest.mark.django_db(transaction=True)

EXTERNAL_USER_ID = "user_automations"
OTHER_USER_ID = "user_other_automations"
AUTH_HEADERS = {"X-User-Id": EXTERNAL_USER_ID}
AUTOMATIONS = "/api/v1/automations"

JANUARY = datetime(2026, 1, 10, tzinfo=UTC)
FEBRUARY = datetime(2026, 2, 10, tzinfo=UTC)
MARCH = datetime(2026, 3, 10, tzinfo=UTC)

COFFEE_FILTER = {"and": [{"field_name": "name", "operator": "icontains", "value": "coffee"}]}
CACHE_PREFIXES = ("read:automations:*", "ver:automations:*")

# `None` is a meaningful filter_body — it means the rule is unconditional —
# so the helper needs a sentinel to tell it from "not supplied".
UNSET = object()


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


async def _automation(
    *,
    name: str = "Auto-categorise coffee shops",
    enabled: bool = True,
    trigger_type: str = "event",
    trigger_event: str = "transaction.created",
    trigger_schedule: str = "",
    filter_body: dict | None = UNSET,  # type: ignore[assignment]
    created_at: datetime = FEBRUARY,
    deleted_at: datetime | None = None,
    owner: str = EXTERNAL_USER_ID,
) -> AutomationReadModel:
    return await AutomationReadModel.objects.acreate(
        id=uuid.uuid4(),
        user_id=await _user_id(owner),
        name=name,
        icon="tag",
        enabled=enabled,
        trigger_type=trigger_type,
        trigger_event=trigger_event,
        trigger_schedule=trigger_schedule,
        filter_body=COFFEE_FILTER if filter_body is UNSET else filter_body,
        effects=[{"type": "set_category", "params": {"category": "Dining"}}],
        created_at=created_at,
        deleted_at=deleted_at,
    )


def _timestamp(moment: datetime) -> Timestamp:
    stamp = Timestamp()
    stamp.FromDatetime(moment)
    return stamp


async def _dispatch(message, seq: int) -> None:
    router = KafkaEventRouter()
    _subscribe_all_events(router)
    await router.dispatch(make_event(message, outbox_seq=seq))


# --- shape ------------------------------------------------------------------


async def test_a_rule_carries_its_whole_definition():
    await _automation()

    row = body_of(await as_user(AUTOMATIONS))["data"][0]

    assert row["name"] == "Auto-categorise coffee shops"
    assert row["enabled"] is True
    assert row["trigger"]["type"] == "event"
    assert row["trigger"]["event"] == "transaction.created"
    assert row["trigger"]["filter_body"] == COFFEE_FILTER
    assert row["effects"] == [{"type": "set_category", "params": {"category": "Dining"}}]
    assert row["runs"] == 0
    assert row["last_run_at"] is None


async def test_both_trigger_selectors_are_always_present():
    """The inapplicable one is `null` rather than an omitted key, so a client
    reads `trigger.schedule` without guarding."""

    await _automation(trigger_type="schedule", trigger_event="", trigger_schedule="monthly")

    trigger = body_of(await as_user(AUTOMATIONS))["data"][0]["trigger"]

    assert trigger["event"] is None
    assert trigger["schedule"] == "monthly"


async def test_an_unconditional_rule_carries_a_null_filter_body():
    """`null` means "always", which is why an empty group is refused rather
    than meaning the same thing."""

    await _automation(filter_body=None)

    assert body_of(await as_user(AUTOMATIONS))["data"][0]["trigger"]["filter_body"] is None


# --- ordering and filters ---------------------------------------------------


async def test_the_list_is_newest_first_which_reverses_evaluation_order():
    """The list shows newest first because that is how a user thinks about
    their rules; the engine runs oldest first so later rules can override."""

    await _automation(name="older", created_at=JANUARY)
    await _automation(name="newer", created_at=MARCH)

    payload = body_of(await as_user(AUTOMATIONS))

    assert [row["name"] for row in payload["data"]] == ["newer", "older"]


async def test_enabled_is_a_tristate():
    await _automation(name="on", enabled=True)
    await _automation(name="off", enabled=False)

    both = body_of(await as_user(AUTOMATIONS))
    on = body_of(await as_user(f"{AUTOMATIONS}?enabled=true"))
    off = body_of(await as_user(f"{AUTOMATIONS}?enabled=false"))

    assert {row["name"] for row in both["data"]} == {"on", "off"}
    assert [row["name"] for row in on["data"]] == ["on"]
    assert [row["name"] for row in off["data"]] == ["off"]


async def test_a_non_boolean_enabled_is_rejected():
    response = await as_user(f"{AUTOMATIONS}?enabled=maybe")

    assert response.status_code == 422
    assert body_of(response)["error"]["details"][0]["field"] == "enabled"


async def test_a_deleted_rule_leaves_the_list_but_still_resolves_by_id():
    """DELETE answers with the rule it removed, so a client re-reading that id
    should still find it."""

    deleted = await _automation(name="gone", deleted_at=MARCH)

    listed = body_of(await as_user(AUTOMATIONS))
    fetched = await as_user(f"{AUTOMATIONS}/{deleted.id}")

    assert listed["data"] == []
    assert fetched.status_code == 200
    assert body_of(fetched)["data"]["deleted_at"] == "2026-03-10T00:00:00+00:00"


async def test_the_list_does_not_show_someone_else_s_rules():
    await _automation(name="mine")
    await _automation(name="theirs", owner=OTHER_USER_ID)

    assert [row["name"] for row in body_of(await as_user(AUTOMATIONS))["data"]] == ["mine"]


async def test_someone_else_s_rule_is_not_found_by_id():
    theirs = await _automation(owner=OTHER_USER_ID)

    assert (await as_user(f"{AUTOMATIONS}/{theirs.id}")).status_code == 404


async def test_the_detail_returns_the_identical_shape():
    automation = await _automation()

    listed = body_of(await as_user(AUTOMATIONS))["data"][0]
    fetched = body_of(await as_user(f"{AUTOMATIONS}/{automation.id}"))["data"]

    assert fetched == listed


# --- projection -------------------------------------------------------------


def _created(automation_id: str, user_id: int, **overrides) -> AutomationCreated:
    message = AutomationCreated(
        event_id=f"evt-{automation_id[:8]}",
        automation_id=automation_id,
        user_external_id=EXTERNAL_USER_ID,
        user_id=user_id,
        name=overrides.get("name", "Auto-categorise coffee shops"),
        icon="tag",
        enabled=overrides.get("enabled", True),
        trigger=AutomationTrigger(
            trigger_type="event",
            event="transaction.created",
            filter_body_json=json.dumps(COFFEE_FILTER),
        ),
        effects=[
            AutomationEffect(
                effect_type="set_category",
                params_json=json.dumps({"category": "Dining"}),
            )
        ],
        created_at=_timestamp(FEBRUARY),
    )

    return message


async def test_a_created_event_projects_the_condition_and_the_effects():
    await _dispatch(_created(str(uuid.uuid4()), await _user_id()), seq=1)

    row = body_of(await as_user(AUTOMATIONS))["data"][0]

    assert row["trigger"]["filter_body"] == COFFEE_FILTER
    assert row["effects"][0]["params"] == {"category": "Dining"}


async def test_an_update_replaces_the_rule_whole():
    """`trigger` and `effects` are replaced, never merged: deep-merging a
    condition tree has no sane definition."""

    automation_id = str(uuid.uuid4())
    user_id = await _user_id()
    await _dispatch(_created(automation_id, user_id), seq=1)

    await _dispatch(
        AutomationUpdated(
            event_id="evt-u1",
            automation_id=automation_id,
            user_external_id=EXTERNAL_USER_ID,
            user_id=user_id,
            name="Renamed",
            icon="tag",
            enabled=False,
            trigger=AutomationTrigger(trigger_type="schedule", schedule="monthly"),
            effects=[
                AutomationEffect(
                    effect_type="notify",
                    params_json=json.dumps({"severity": "info", "title": "Ran"}),
                )
            ],
            updated_at=_timestamp(MARCH),
        ),
        seq=2,
    )

    row = body_of(await as_user(AUTOMATIONS))["data"][0]

    assert row["name"] == "Renamed"
    assert row["enabled"] is False
    assert row["trigger"]["type"] == "schedule"
    assert row["trigger"]["event"] is None
    assert row["trigger"]["filter_body"] is None
    assert [effect["type"] for effect in row["effects"]] == ["notify"]


async def test_a_delete_event_removes_the_rule_from_the_list():
    automation = await _automation()

    await _dispatch(
        AutomationDeleted(
            event_id="evt-d1",
            automation_id=str(automation.id),
            user_external_id=EXTERNAL_USER_ID,
            user_id=automation.user_id,
            deleted_at=_timestamp(MARCH),
        ),
        seq=3,
    )

    assert body_of(await as_user(AUTOMATIONS))["data"] == []


async def test_the_engine_s_counters_are_projected_not_derived():
    """`runs` counts matches that APPLIED effects, which only the engine can
    know — the read side never computes it."""

    automation = await _automation()

    await _dispatch(
        AutomationRan(
            event_id="evt-r1",
            automation_id=str(automation.id),
            user_external_id=EXTERNAL_USER_ID,
            user_id=automation.user_id,
            runs=14,
            last_run_at=_timestamp(MARCH),
        ),
        seq=4,
    )

    row = body_of(await as_user(AUTOMATIONS))["data"][0]

    assert row["runs"] == 14
    assert row["last_run_at"] == "2026-03-10T00:00:00+00:00"

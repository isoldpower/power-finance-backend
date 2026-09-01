"""The needs-action queue.

Every action is a different decision but they are NOT different resources: the
envelope is identical and what varies is `resolutions`. These tests hold that
line — nothing here branches on `kind`.
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
    ActionRaised,
    ActionResolution,
    ActionResolved,
    ActionSeverity,
    ActionSource,
    ActionStatus,
    ResolutionIntent,
)

from data_read_core.shared.postgres_orm import ActionReadModel
from data_read_core.shared.redis_cache import get_redis

pytestmark = pytest.mark.django_db(transaction=True)

EXTERNAL_USER_ID = "user_actions"
OTHER_USER_ID = "user_other_actions"
AUTH_HEADERS = {"X-User-Id": EXTERNAL_USER_ID}
ACTIONS = "/api/v1/actions"

JANUARY = datetime(2026, 1, 10, tzinfo=UTC)
FEBRUARY = datetime(2026, 2, 10, tzinfo=UTC)
MARCH = datetime(2026, 3, 10, tzinfo=UTC)

CACHE_PREFIXES = ("read:actions:*", "ver:actions:*")

RANKS = {"info": 1, "warning": 2, "critical": 3}


def as_user(path: str, headers: dict | None = None):
    return AsyncClient().get(path, headers=headers or AUTH_HEADERS)


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


async def _action(
    *,
    kind: str = "uncategorized",
    source: str = "assistant",
    severity: str = "info",
    status: str = "pending",
    title: str = "3 transactions need a category",
    subject_type: str = "",
    subject_id: str = "",
    money_amount: str | None = None,
    money_currency: str = "",
    group_key: str = "",
    occurrences: int = 1,
    expires_at: datetime | None = None,
    created_at: datetime = FEBRUARY,
    owner: str = EXTERNAL_USER_ID,
    resolutions: list | None = None,
) -> ActionReadModel:
    from decimal import Decimal

    return await ActionReadModel.objects.acreate(
        id=uuid.uuid4(),
        user_id=await _user_id(owner),
        source=source,
        kind=kind,
        severity=severity,
        severity_rank=RANKS[severity],
        status=status,
        title=title,
        body="",
        subject_type=subject_type,
        subject_id=subject_id,
        money_amount=Decimal(money_amount) if money_amount else None,
        money_currency=money_currency,
        group_key=group_key,
        occurrences=occurrences,
        last_seen_at=created_at,
        expires_at=expires_at,
        created_at=created_at,
        resolutions=resolutions
        if resolutions is not None
        else [
            {
                "resolution_id": "apply",
                "label": "Categorise",
                "intent": "primary",
                "applies": True,
            }
        ],
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


async def test_an_action_carries_the_documented_shape():
    await _action(
        source="scheduler",
        kind="insufficient_funds",
        severity="critical",
        title="Netflix charges tomorrow",
        subject_type="wallet",
        subject_id="9a1e4c2b-0d7f-4a11-9c33-2b7e5f8a1d40",
        money_amount="15.99",
        money_currency="USD",
        group_key="recurring:netflix",
        occurrences=3,
        expires_at=MARCH,
    )

    row = body_of(await as_user(ACTIONS))["data"][0]

    assert row["source"] == "scheduler"
    assert row["kind"] == "insufficient_funds"
    assert row["severity"] == "critical"
    assert row["status"] == "pending"
    assert row["subject"] == {
        "type": "wallet",
        "id": "9a1e4c2b-0d7f-4a11-9c33-2b7e5f8a1d40",
    }
    assert row["money"] == {"amount": "15.99", "currency": "USD"}
    assert row["group_key"] == "recurring:netflix"
    assert row["occurrences"] == 3
    assert row["expires_at"] == "2026-03-10T00:00:00+00:00"
    assert row["resolved_at"] is None


async def test_an_action_about_no_amount_carries_no_money():
    """Absent rather than zero: an action not about an amount has no money,
    which is a different thing from one about nothing."""

    await _action()

    assert body_of(await as_user(ACTIONS))["data"][0]["money"] is None


async def test_a_non_recurring_action_has_a_null_group_key_and_one_occurrence():
    await _action()

    row = body_of(await as_user(ACTIONS))["data"][0]

    assert row["group_key"] is None
    assert row["occurrences"] == 1


async def test_resolutions_carry_their_rendering_hint_and_effect():
    await _action(
        resolutions=[
            {
                "resolution_id": "top_up",
                "label": "Move money",
                "intent": "primary",
                "applies": False,
            },
            {
                "resolution_id": "dismiss",
                "label": "Ignore",
                "intent": "secondary",
                "applies": False,
            },
        ]
    )

    resolutions = body_of(await as_user(ACTIONS))["data"][0]["resolutions"]

    assert [resolution["id"] for resolution in resolutions] == ["top_up", "dismiss"]
    assert resolutions[0]["intent"] == "primary"
    assert resolutions[0]["applies"] is False


async def test_the_dismissal_flag_never_reaches_the_client():
    """It decides which status the write side produces. A client renders
    buttons; it does not need to know which one the server calls dismissal."""

    await _action(
        resolutions=[
            {
                "resolution_id": "dismiss",
                "label": "Ignore",
                "intent": "secondary",
                "applies": False,
                "dismissal": True,
            }
        ]
    )

    resolution = body_of(await as_user(ACTIONS))["data"][0]["resolutions"][0]

    assert "dismissal" not in resolution


# --- ordering and filters ---------------------------------------------------


async def test_the_queue_leads_with_urgency():
    """Unlike the notification feed this IS a list to be worked through, so a
    critical action outranks an older informational one."""

    await _action(title="old critical", severity="critical", created_at=JANUARY)
    await _action(title="new info", severity="info", created_at=MARCH)
    await _action(title="mid warning", severity="warning", created_at=FEBRUARY)

    payload = body_of(await as_user(ACTIONS))

    assert [row["title"] for row in payload["data"]] == [
        "old critical",
        "mid warning",
        "new info",
    ]


async def test_equal_urgency_falls_back_to_newest_first():
    await _action(title="older", severity="warning", created_at=JANUARY)
    await _action(title="newer", severity="warning", created_at=MARCH)

    payload = body_of(await as_user(ACTIONS))

    assert [row["title"] for row in payload["data"]] == ["newer", "older"]


async def test_the_queue_shows_pending_by_default():
    await _action(title="open")
    await _action(title="answered", status="resolved")

    payload = body_of(await as_user(ACTIONS))

    assert [row["title"] for row in payload["data"]] == ["open"]


async def test_status_selects_another_slice_of_the_queue():
    await _action(title="open")
    await _action(title="answered", status="resolved")
    await _action(title="ignored", status="dismissed")

    resolved = body_of(await as_user(f"{ACTIONS}?status=resolved"))
    dismissed = body_of(await as_user(f"{ACTIONS}?status=dismissed"))

    assert [row["title"] for row in resolved["data"]] == ["answered"]
    assert [row["title"] for row in dismissed["data"]] == ["ignored"]


async def test_both_producers_share_one_collection():
    """Splitting them would force the client to merge two independently ordered
    lists, which cannot be paginated by keyset."""

    await _action(title="from assistant", source="assistant")
    await _action(title="from scheduler", source="scheduler")

    both = body_of(await as_user(ACTIONS))
    only_scheduler = body_of(await as_user(f"{ACTIONS}?source=scheduler"))

    assert len(both["data"]) == 2
    assert [row["title"] for row in only_scheduler["data"]] == ["from scheduler"]


async def test_severity_narrows_the_queue():
    await _action(title="loud", severity="critical")
    await _action(title="quiet", severity="info")

    payload = body_of(await as_user(f"{ACTIONS}?severity=critical"))

    assert [row["title"] for row in payload["data"]] == ["loud"]


@pytest.mark.parametrize(
    ("parameter", "value"),
    [("status", "archived"), ("source", "cron"), ("severity", "apocalyptic")],
)
async def test_an_unknown_filter_value_is_rejected(parameter: str, value: str):
    """Quietly answering about a different slice than the caller asked for is
    worse than refusing."""

    response = await as_user(f"{ACTIONS}?{parameter}={value}")

    assert response.status_code == 422
    assert body_of(response)["error"]["details"][0]["field"] == parameter


async def test_the_queue_does_not_show_someone_else_s_actions():
    await _action(title="mine")
    await _action(title="theirs", owner=OTHER_USER_ID)

    payload = body_of(await as_user(ACTIONS))

    assert [row["title"] for row in payload["data"]] == ["mine"]


async def test_the_queue_pages_by_urgency_then_recency():
    for index in range(3):
        await _action(
            title=f"critical-{index}",
            severity="critical",
            created_at=datetime(2026, 2, 10 + index, tzinfo=UTC),
        )
    await _action(title="info", severity="info", created_at=MARCH)

    first = body_of(await as_user(f"{ACTIONS}?limit=2"))
    second = body_of(await as_user(f"{ACTIONS}?limit=2&cursor={first['meta']['next_cursor']}"))

    assert [row["title"] for row in first["data"]] == ["critical-2", "critical-1"]
    assert [row["title"] for row in second["data"]] == ["critical-0", "info"]


# --- projection -------------------------------------------------------------


def _raised(action_id: str, user_id: int, **overrides) -> ActionRaised:
    message = ActionRaised(
        event_id=f"evt-{action_id[:8]}",
        action_id=action_id,
        user_external_id=EXTERNAL_USER_ID,
        user_id=user_id,
        source=overrides.get("source", ActionSource.ACTION_SOURCE_SCHEDULER),
        kind=overrides.get("kind", "insufficient_funds"),
        severity=overrides.get("severity", ActionSeverity.ACTION_SEVERITY_CRITICAL),
        title=overrides.get("title", "Netflix charges tomorrow"),
        body="Card has 4.20 USD available.",
        subject_type=overrides.get("subject_type", "wallet"),
        subject_id=overrides.get("subject_id", "9a1e4c2b"),
        money_amount=overrides.get("money_amount", "15.99"),
        money_currency=overrides.get("money_currency", "USD"),
        group_key=overrides.get("group_key", ""),
        occurrences=overrides.get("occurrences", 1),
        resolutions=[
            ActionResolution(
                resolution_id="top_up",
                label="Move money",
                intent=ResolutionIntent.RESOLUTION_INTENT_PRIMARY,
                applies=True,
            ),
            ActionResolution(
                resolution_id="dismiss",
                label="Ignore",
                intent=ResolutionIntent.RESOLUTION_INTENT_SECONDARY,
                dismissal=True,
            ),
        ],
    )
    message.last_seen_at.CopyFrom(_timestamp(overrides.get("last_seen_at", FEBRUARY)))
    message.created_at.CopyFrom(_timestamp(FEBRUARY))

    return message


async def test_a_raised_event_projects_the_whole_action():
    """The event carries the resolutions because the read side has no way to
    know what the producer decided to offer."""

    await _dispatch(_raised(str(uuid.uuid4()), await _user_id()), seq=1)

    row = body_of(await as_user(ACTIONS))["data"][0]

    assert row["severity"] == "critical"
    assert row["source"] == "scheduler"
    assert row["money"] == {"amount": "15.99", "currency": "USD"}
    assert [resolution["id"] for resolution in row["resolutions"]] == ["top_up", "dismiss"]
    assert row["resolutions"][0]["intent"] == "primary"


async def test_a_recurring_condition_updates_one_row_rather_than_appending():
    """A daily check until payday bumps `occurrences` on ONE action instead of
    burying the queue it is trying to surface."""

    action_id = str(uuid.uuid4())
    user_id = await _user_id()

    await _dispatch(_raised(action_id, user_id, group_key="recurring:netflix"), seq=1)
    await _dispatch(
        _raised(
            action_id,
            user_id,
            group_key="recurring:netflix",
            occurrences=2,
            last_seen_at=MARCH,
        ),
        seq=2,
    )

    payload = body_of(await as_user(ACTIONS))

    assert payload["meta"]["total"] == 1
    assert payload["data"][0]["occurrences"] == 2
    assert payload["data"][0]["last_seen_at"] == "2026-03-10T00:00:00+00:00"


async def test_an_event_with_no_severity_projects_as_info():
    await _dispatch(
        _raised(
            str(uuid.uuid4()),
            await _user_id(),
            severity=ActionSeverity.ACTION_SEVERITY_UNSPECIFIED,
        ),
        seq=1,
    )

    assert body_of(await as_user(ACTIONS))["data"][0]["severity"] == "info"


async def test_answering_empties_the_choices_and_leaves_the_pending_queue():
    action = await _action()

    await _dispatch(
        ActionResolved(
            event_id="evt-r1",
            action_id=str(action.id),
            user_external_id=EXTERNAL_USER_ID,
            user_id=action.user_id,
            status=ActionStatus.ACTION_STATUS_RESOLVED,
            resolution_id="apply",
            resolved_at=_timestamp(MARCH),
            updated_at=_timestamp(MARCH),
        ),
        seq=2,
    )

    pending = body_of(await as_user(ACTIONS))
    resolved = body_of(await as_user(f"{ACTIONS}?status=resolved"))

    assert pending["data"] == []
    assert resolved["data"][0]["resolutions"] == []
    assert resolved["data"][0]["resolved_at"] == "2026-03-10T00:00:00+00:00"


async def test_dismissal_projects_as_dismissed_not_resolved():
    action = await _action()

    await _dispatch(
        ActionResolved(
            event_id="evt-r2",
            action_id=str(action.id),
            user_external_id=EXTERNAL_USER_ID,
            user_id=action.user_id,
            status=ActionStatus.ACTION_STATUS_DISMISSED,
            resolution_id="dismiss",
            resolved_at=_timestamp(MARCH),
            updated_at=_timestamp(MARCH),
        ),
        seq=3,
    )

    assert body_of(await as_user(f"{ACTIONS}?status=dismissed"))["data"][0]["status"] == "dismissed"


async def test_a_redelivered_answer_cannot_restate_the_first_one():
    """Only a PENDING row is answered, so a replay cannot turn a dismissal into
    a resolution or move `resolved_at`."""

    action = await _action()
    common = dict(
        action_id=str(action.id),
        user_external_id=EXTERNAL_USER_ID,
        user_id=action.user_id,
        resolved_at=_timestamp(FEBRUARY),
        updated_at=_timestamp(FEBRUARY),
    )

    await _dispatch(
        ActionResolved(
            event_id="evt-r3",
            status=ActionStatus.ACTION_STATUS_DISMISSED,
            resolution_id="dismiss",
            **common,
        ),
        seq=4,
    )
    await _dispatch(
        ActionResolved(
            event_id="evt-r4",
            status=ActionStatus.ACTION_STATUS_RESOLVED,
            resolution_id="apply",
            **{**common, "resolved_at": _timestamp(MARCH)},
        ),
        seq=5,
    )

    dismissed = body_of(await as_user(f"{ACTIONS}?status=dismissed"))

    assert len(dismissed["data"]) == 1
    assert dismissed["data"][0]["resolved_at"] == "2026-02-10T00:00:00+00:00"
    assert body_of(await as_user(f"{ACTIONS}?status=resolved"))["data"] == []

"""The notification backlog and its badge.

A notification is display-only: nothing is derived from it, which is why the
stream can carry the whole resource and why this slice has no money in it.
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
    NotificationCreated,
    NotificationsAcknowledged,
    NotificationSeverity,
)

from data_read_core.shared.postgres_orm import NotificationReadModel
from data_read_core.shared.redis_cache import get_redis

pytestmark = pytest.mark.django_db(transaction=True)

EXTERNAL_USER_ID = "user_notifications"
OTHER_USER_ID = "user_other_notifications"
AUTH_HEADERS = {"X-User-Id": EXTERNAL_USER_ID}

NOTIFICATIONS = "/api/v1/notifications"
COUNT = "/api/v1/notifications/count"

JANUARY = datetime(2026, 1, 10, tzinfo=UTC)
FEBRUARY = datetime(2026, 2, 10, tzinfo=UTC)
MARCH = datetime(2026, 3, 10, tzinfo=UTC)

CACHE_PREFIXES = ("read:notification*", "ver:notifications:*")


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


async def _notification(
    *,
    title: str = "Visa Credit near limit",
    body: str = "You are at 82% of your limit.",
    severity: str = "info",
    subject_type: str = "",
    subject_id: str = "",
    acknowledged_at: datetime | None = None,
    created_at: datetime = FEBRUARY,
    owner: str = EXTERNAL_USER_ID,
) -> NotificationReadModel:
    return await NotificationReadModel.objects.acreate(
        id=uuid.uuid4(),
        user_id=await _user_id(owner),
        severity=severity,
        title=title,
        body=body,
        subject_type=subject_type,
        subject_id=subject_id,
        acknowledged_at=acknowledged_at,
        created_at=created_at,
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


async def test_a_notification_carries_the_documented_shape():
    await _notification(
        severity="critical",
        subject_type="wallet",
        subject_id="9a1e4c2b-0d7f-4a11-9c33-2b7e5f8a1d40",
    )

    payload = body_of(await as_user(NOTIFICATIONS))

    assert payload["data"][0] == {
        "id": payload["data"][0]["id"],
        "severity": "critical",
        "title": "Visa Credit near limit",
        "body": "You are at 82% of your limit.",
        "subject": {
            "type": "wallet",
            "id": "9a1e4c2b-0d7f-4a11-9c33-2b7e5f8a1d40",
        },
        "acknowledged_at": None,
        "created_at": "2026-02-10T00:00:00+00:00",
        "updated_at": None,
        "deleted_at": None,
    }


async def test_acknowledged_at_is_a_timestamp_not_a_boolean():
    """The fact and its time are one field, the same shape `deleted_at` uses."""

    await _notification(acknowledged_at=MARCH)

    payload = body_of(await as_user(NOTIFICATIONS))

    assert payload["data"][0]["acknowledged_at"] == "2026-03-10T00:00:00+00:00"


async def test_a_half_filled_subject_is_null():
    """A reference needs both halves to be followable."""

    await _notification(subject_type="wallet", subject_id="")

    payload = body_of(await as_user(NOTIFICATIONS))

    assert payload["data"][0]["subject"] is None


async def test_the_producer_s_payload_bag_never_reaches_the_client():
    notification = await _notification()
    notification.payload = {"internal": "bookkeeping"}
    await notification.asave()

    payload = body_of(await as_user(NOTIFICATIONS))

    assert "payload" not in payload["data"][0]


# --- ordering and filters ---------------------------------------------------


async def test_severity_does_not_reorder_the_feed():
    """This is a feed to be read, not a queue to be worked through: a critical
    notification from Tuesday does NOT outrank an info from this morning."""

    await _notification(title="old critical", severity="critical", created_at=JANUARY)
    await _notification(title="new info", severity="info", created_at=MARCH)

    payload = body_of(await as_user(NOTIFICATIONS))

    assert [row["title"] for row in payload["data"]] == ["new info", "old critical"]


async def test_acknowledged_is_a_tristate():
    """Absent means BOTH — which is not the same request as either value."""

    await _notification(title="read", acknowledged_at=MARCH)
    await _notification(title="unread")

    both = body_of(await as_user(NOTIFICATIONS))
    read = body_of(await as_user(f"{NOTIFICATIONS}?acknowledged=true"))
    unread = body_of(await as_user(f"{NOTIFICATIONS}?acknowledged=false"))

    assert {row["title"] for row in both["data"]} == {"read", "unread"}
    assert [row["title"] for row in read["data"]] == ["read"]
    assert [row["title"] for row in unread["data"]] == ["unread"]


async def test_the_severity_filter_narrows_the_feed():
    await _notification(title="loud", severity="critical")
    await _notification(title="quiet", severity="info")

    payload = body_of(await as_user(f"{NOTIFICATIONS}?severity=critical"))

    assert [row["title"] for row in payload["data"]] == ["loud"]
    assert payload["meta"]["total"] == 1


async def test_an_unknown_severity_is_rejected():
    response = await as_user(f"{NOTIFICATIONS}?severity=apocalyptic")

    assert response.status_code == 422
    assert body_of(response)["error"]["details"][0]["field"] == "severity"


async def test_a_non_boolean_acknowledged_is_rejected():
    response = await as_user(f"{NOTIFICATIONS}?acknowledged=maybe")

    assert response.status_code == 422
    assert body_of(response)["error"]["details"][0]["field"] == "acknowledged"


async def test_the_feed_does_not_show_someone_else_s_notifications():
    await _notification(title="mine")
    await _notification(title="theirs", owner=OTHER_USER_ID)

    payload = body_of(await as_user(NOTIFICATIONS))

    assert [row["title"] for row in payload["data"]] == ["mine"]


# --- GET /notifications/count -----------------------------------------------


async def test_the_badge_counts_unacknowledged_against_the_total():
    await _notification(acknowledged_at=MARCH)
    await _notification()
    await _notification()

    payload = body_of(await as_user(COUNT))

    assert payload["data"] == {"unacknowledged": 2, "total": 3}
    assert payload["meta"] == {}


async def test_the_badge_is_zero_rather_than_absent_for_a_new_user():
    payload = body_of(await as_user(COUNT))

    assert payload["data"] == {"unacknowledged": 0, "total": 0}


async def test_the_badge_ignores_someone_else_s_notifications():
    await _notification(owner=OTHER_USER_ID)

    payload = body_of(await as_user(COUNT))

    assert payload["data"]["total"] == 0


# --- projection -------------------------------------------------------------


async def test_a_created_event_projects_the_whole_shape():
    await _dispatch(
        NotificationCreated(
            event_id="evt-n1",
            notification_id=str(uuid.uuid4()),
            user_id=await _user_id(),
            user_external_id=EXTERNAL_USER_ID,
            title="Transfer completed",
            body="500.00 USD moved.",
            severity=NotificationSeverity.NOTIFICATION_SEVERITY_WARNING,
            subject_type="transaction",
            subject_id="b21d7e40-9c3a-4f18-88de-1a5c6b0e7f92",
            created_at=_timestamp(FEBRUARY),
        ),
        seq=1,
    )

    payload = body_of(await as_user(NOTIFICATIONS))

    assert payload["data"][0]["severity"] == "warning"
    assert payload["data"][0]["title"] == "Transfer completed"
    assert payload["data"][0]["subject"] == {
        "type": "transaction",
        "id": "b21d7e40-9c3a-4f18-88de-1a5c6b0e7f92",
    }
    assert payload["data"][0]["acknowledged_at"] is None


async def test_an_event_with_no_severity_projects_as_info():
    """A producer that never set the field is saying "ordinary", not "unknown
    urgency the client must handle"."""

    await _dispatch(
        NotificationCreated(
            event_id="evt-n2",
            notification_id=str(uuid.uuid4()),
            user_id=await _user_id(),
            user_external_id=EXTERNAL_USER_ID,
            title="Something happened",
            body="...",
            created_at=_timestamp(FEBRUARY),
        ),
        seq=2,
    )

    payload = body_of(await as_user(NOTIFICATIONS))

    assert payload["data"][0]["severity"] == "info"


async def test_an_acknowledgement_records_when_it_happened():
    notification = await _notification()

    await _dispatch(
        NotificationsAcknowledged(
            event_id="evt-a1",
            notification_ids=[str(notification.id)],
            user_id=notification.user_id,
            acknowledged_at=_timestamp(MARCH),
        ),
        seq=3,
    )

    payload = body_of(await as_user(NOTIFICATIONS))

    assert payload["data"][0]["acknowledged_at"] == "2026-03-10T00:00:00+00:00"
    assert payload["data"][0]["updated_at"] == "2026-03-10T00:00:00+00:00"


async def test_a_redelivered_acknowledgement_does_not_move_the_timestamp():
    """`acknowledged_at` records when the user saw it. A redelivered event is
    the same fact arriving twice, not a second reading."""

    notification = await _notification(acknowledged_at=FEBRUARY)

    await _dispatch(
        NotificationsAcknowledged(
            event_id="evt-a2",
            notification_ids=[str(notification.id)],
            user_id=notification.user_id,
            acknowledged_at=_timestamp(MARCH),
        ),
        seq=4,
    )

    payload = body_of(await as_user(NOTIFICATIONS))

    assert payload["data"][0]["acknowledged_at"] == "2026-02-10T00:00:00+00:00"


async def test_an_acknowledgement_moves_the_badge():
    notification = await _notification()
    assert body_of(await as_user(COUNT))["data"]["unacknowledged"] == 1

    await _dispatch(
        NotificationsAcknowledged(
            event_id="evt-a3",
            notification_ids=[str(notification.id)],
            user_id=notification.user_id,
            acknowledged_at=_timestamp(MARCH),
        ),
        seq=5,
    )

    payload = body_of(await as_user(COUNT))

    assert payload["data"] == {"unacknowledged": 0, "total": 1}

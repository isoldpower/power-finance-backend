"""The cursor wire format, which is shared with the Django services.

A client stores one kind of opaque token whichever service answered it, so the
encoding is pinned here rather than left to whatever `json.dumps` does today.
"""

import base64
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from service_core.shared.http_contract import ApiError
from service_core.shared.pagination import (
    DEFAULT_LIMIT,
    MAXIMUM_LIMIT,
    MESSAGE_FEED_ORDER,
    MINIMUM_LIMIT,
    PageDirection,
    build_page,
    decode_cursor,
    decode_message_anchor,
    encode_cursor,
    query_fingerprint,
    resolve_limit,
)

NOON = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
FINGERPRINT = query_fingerprint(MESSAGE_FEED_ORDER)


def _row(minute: int) -> tuple:
    return (NOON.replace(minute=minute), uuid4())


def _key(row: tuple) -> tuple:
    return row


def test_a_cursor_round_trips():
    message_id = uuid4()

    cursor = encode_cursor(PageDirection.NEXT, (NOON, message_id), FINGERPRINT)
    anchor = decode_message_anchor(decode_cursor(cursor, FINGERPRINT))

    assert anchor == (NOON, message_id)


def test_a_cursor_carries_its_direction():
    cursor = encode_cursor(PageDirection.PREVIOUS, (NOON, uuid4()), FINGERPRINT)

    assert decode_cursor(cursor, FINGERPRINT).backwards is True


def test_the_payload_is_the_shape_the_other_services_mint():
    """`{v, d, k, f}`, base64url, unpadded."""

    raw = encode_cursor(PageDirection.NEXT, (NOON, UUID(int=1)), FINGERPRINT)

    assert "=" not in raw
    padded = raw + "=" * (-len(raw) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded))

    assert payload["v"] == 1
    assert payload["d"] == "next"
    assert payload["f"] == FINGERPRINT
    assert payload["k"] == [NOON.isoformat(), str(UUID(int=1))]


def test_a_cursor_from_another_query_is_refused():
    """Carrying one across a filter change would silently skip or repeat rows."""

    cursor = encode_cursor(PageDirection.NEXT, (NOON, uuid4()), FINGERPRINT)

    with pytest.raises(ApiError) as refusal:
        decode_cursor(cursor, query_fingerprint("something:else"))

    assert str(refusal.value.code) == "cursor_mismatch"


@pytest.mark.parametrize(
    "raw", ["not-a-cursor", "", "!!!!", base64.urlsafe_b64encode(b"[]").decode()]
)
def test_an_unreadable_cursor_is_refused(raw):
    with pytest.raises(ApiError) as refusal:
        decode_cursor(raw, FINGERPRINT)

    assert str(refusal.value.code) == "cursor_invalid"


def test_a_cursor_from_a_future_version_is_refused():
    payload = json.dumps({"v": 2, "d": "next", "k": [], "f": FINGERPRINT})
    raw = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")

    with pytest.raises(ApiError) as refusal:
        decode_cursor(raw, FINGERPRINT)

    assert str(refusal.value.code) == "cursor_invalid"


def test_the_limit_is_clamped_rather_than_refused():
    assert resolve_limit(None) == DEFAULT_LIMIT
    assert resolve_limit(5000) == MAXIMUM_LIMIT
    assert resolve_limit(0) == MINIMUM_LIMIT
    assert resolve_limit(10) == 10


def test_a_complete_page_navigates_nowhere():
    page = build_page([_row(1)], total=1, limit=25, fingerprint=FINGERPRINT, key_of=_key)

    assert page.next_cursor is None
    assert page.previous_cursor is None
    assert page.meta() == {
        "limit": 25,
        "total": 1,
        "next_cursor": None,
        "prev_cursor": None,
    }


def test_the_lookahead_row_is_trimmed_and_becomes_a_next_cursor():
    rows = [_row(minute) for minute in (3, 2, 1)]

    page = build_page(rows, total=3, limit=2, fingerprint=FINGERPRINT, key_of=_key)

    assert len(page.items) == 2
    assert page.next_cursor is not None
    assert page.previous_cursor is None


def test_a_page_reached_by_a_cursor_can_go_back():
    rows = [_row(minute) for minute in (3, 2)]
    cursor = decode_cursor(encode_cursor(PageDirection.NEXT, _row(4), FINGERPRINT), FINGERPRINT)

    page = build_page(rows, total=4, limit=2, fingerprint=FINGERPRINT, key_of=_key, cursor=cursor)

    assert page.previous_cursor is not None


def test_an_empty_page_mints_no_cursors():
    page = build_page([], total=0, limit=25, fingerprint=FINGERPRINT, key_of=_key)

    assert page.items == []
    assert page.next_cursor is None
    assert page.previous_cursor is None


def test_a_non_integer_limit_leaves_through_the_error_envelope():
    """FastAPI's own validation would answer with `{"detail": [...]}`, which is
    not the error shape this API promises."""

    with pytest.raises(ApiError) as refusal:
        resolve_limit("plenty")

    assert str(refusal.value.code) == "validation_failed"
    assert refusal.value.details[0].field == "limit"


def test_a_blank_limit_reads_as_absent():
    assert resolve_limit("") == DEFAULT_LIMIT
    assert resolve_limit("7") == 7

import pytest

from data_read_core.shared.http_contract import CursorInvalid, CursorMismatch
from data_read_core.shared.pagination import (
    CREATED_AT_DESC,
    CURSOR_CODEC,
    CursorCodec,
    PageDirection,
    query_fingerprint,
)

FINGERPRINT = query_fingerprint(CREATED_AT_DESC)


def test_cursor_round_trips_direction_and_anchor():
    token = CURSOR_CODEC.encode(
        PageDirection.NEXT,
        ["2026-01-01T00:00:00+00:00", "w1"],
        FINGERPRINT,
    )

    decoded = CURSOR_CODEC.decode(token, FINGERPRINT)

    assert decoded.direction is PageDirection.NEXT
    assert decoded.values == ["2026-01-01T00:00:00+00:00", "w1"]


def test_cursor_is_opaque_and_url_safe():
    token = CURSOR_CODEC.encode(PageDirection.NEXT, ["a", "b"], FINGERPRINT)

    assert "=" not in token
    assert "/" not in token
    assert "+" not in token


def test_cursor_minted_for_another_query_is_rejected():
    """A cursor is bound to the order and filter tree that produced it, so an
    edited filter fails instead of walking a different result set."""

    token = CURSOR_CODEC.encode(PageDirection.NEXT, ["a", "b"], FINGERPRINT)
    other_query = query_fingerprint(CREATED_AT_DESC, {"field_name": "amount"})

    with pytest.raises(CursorMismatch):
        CURSOR_CODEC.decode(token, other_query)


@pytest.mark.parametrize(
    "token",
    ["not-base64!!", "", "eyJub3RfanNvbiI6", "e30"],
)
def test_unreadable_cursor_is_rejected(token: str):
    with pytest.raises(CursorInvalid):
        CURSOR_CODEC.decode(token, FINGERPRINT)


def test_cursor_from_another_version_is_rejected():
    older = CursorCodec(version=CURSOR_CODEC.version - 1)
    token = older.encode(PageDirection.NEXT, ["a", "b"], FINGERPRINT)

    with pytest.raises(CursorInvalid):
        CURSOR_CODEC.decode(token, FINGERPRINT)


def test_fingerprint_ignores_key_order_in_the_filter_tree():
    left = query_fingerprint(CREATED_AT_DESC, {"field_name": "amount", "operator": "gte"})
    right = query_fingerprint(CREATED_AT_DESC, {"operator": "gte", "field_name": "amount"})

    assert left == right

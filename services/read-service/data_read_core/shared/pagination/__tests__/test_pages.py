from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from data_read_core.shared.http_contract import ValidationFailed
from data_read_core.shared.pagination import (
    CREATED_AT_DESC,
    CURSOR_CODEC,
    DEFAULT_LIMIT_POLICY,
    CompletePage,
    PageRequest,
    build_page,
)

FACTORY = APIRequestFactory()
START = datetime(2026, 1, 1, tzinfo=UTC)


@dataclass(frozen=True)
class Row:
    id: str
    created_at: str


def rows(count: int) -> list[Row]:
    """Newest first, as every collection in this API is ordered."""

    return [
        Row(id=f"r{index}", created_at=(START - timedelta(days=index)).isoformat())
        for index in range(count)
    ]


def page_request(limit: int = 2, cursor: str | None = None) -> PageRequest:
    query = {"limit": str(limit)}
    if cursor:
        query["cursor"] = cursor

    return PageRequest.from_request(Request(FACTORY.get("/transactions", query)), CREATED_AT_DESC)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, DEFAULT_LIMIT_POLICY.default),
        ("", DEFAULT_LIMIT_POLICY.default),
        ("0", 1),
        ("-5", 1),
        ("5000", 100),
        ("30", 30),
    ],
)
def test_limit_is_clamped_not_rejected(raw, expected):
    assert DEFAULT_LIMIT_POLICY.resolve(raw) == expected


def test_non_integer_limit_fails_validation():
    """Clamping answers "as few / as many as possible"; a non-integer is a bug
    in the caller and says so."""

    with pytest.raises(ValidationFailed):
        DEFAULT_LIMIT_POLICY.resolve("twenty")


def test_first_page_has_no_previous_cursor():
    request = page_request(limit=2)

    page = build_page(rows(3), total=5, request=request)

    assert [row.id for row in page.items] == ["r0", "r1"]
    assert page.previous_cursor is None
    assert page.next_cursor is not None
    assert page.meta()["total"] == 5


def test_last_page_has_no_next_cursor():
    request = page_request(limit=2)

    page = build_page(rows(2), total=2, request=request)

    assert page.next_cursor is None
    assert page.previous_cursor is None


def test_walking_forward_then_back_returns_the_same_page():
    """Keyset pages neither repeat nor skip: the anchor is a position in the
    ordering, not a count of rows to skip."""

    everything = rows(6)

    first_request = page_request(limit=2)
    first = build_page(everything[:3], total=6, request=first_request)

    second_request = page_request(limit=2, cursor=first.next_cursor)
    second = build_page(everything[2:5], total=6, request=second_request)
    assert [row.id for row in second.items] == ["r2", "r3"]

    back_request = page_request(limit=2, cursor=second.previous_cursor)
    # Paging backwards scans in reverse, so the store hands rows back tail-first.
    back = build_page([everything[1], everything[0]], total=6, request=back_request)

    assert [row.id for row in back.items] == ["r0", "r1"]


def test_backward_page_always_offers_a_next_cursor():
    everything = rows(4)
    forward = build_page(everything[:3], total=4, request=page_request(limit=2))

    back_request = page_request(limit=2, cursor=forward.next_cursor)
    decoded = CURSOR_CODEC.decode(forward.next_cursor, back_request.fingerprint)
    assert decoded.direction.value == "next"


def test_empty_collection_has_both_cursors_null():
    page = build_page([], total=0, request=page_request())

    assert page.items == []
    assert page.next_cursor is None
    assert page.previous_cursor is None


def test_non_paginated_collection_reports_null_limit():
    page = CompletePage([Row("r0", START.isoformat())])

    assert page.meta() == {
        "limit": None,
        "total": 1,
        "next_cursor": None,
        "prev_cursor": None,
    }


def test_embedded_collection_meta_is_namespaced():
    page = build_page(rows(1), total=1, request=page_request())

    assert set(page.meta(namespace="history")) == {"history"}

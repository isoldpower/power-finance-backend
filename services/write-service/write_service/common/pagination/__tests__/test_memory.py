"""The in-memory keyset must page exactly like the database one: the gateway can
reroute mid-walk, so a cursor minted by one has to mean the same to the other."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from write_service.common.pagination import (
    CREATED_AT_DESC,
    CURSOR_CODEC,
    PageRequest,
    build_page,
    keyset_slice,
    query_fingerprint,
)

START = datetime(2026, 1, 1, tzinfo=UTC)
FINGERPRINT = query_fingerprint(CREATED_AT_DESC)


@dataclass(frozen=True)
class Row:
    id: str
    created_at: datetime


def rows(count: int) -> list[Row]:
    """Deliberately shuffled: the slice is responsible for the ordering."""

    unordered = [
        Row(id=f"r{index}", created_at=START - timedelta(days=index)) for index in range(count)
    ]

    return unordered[::-1]


def page_request(limit: int, cursor: str | None = None) -> PageRequest:
    return PageRequest(
        limit=limit,
        order=CREATED_AT_DESC,
        fingerprint=FINGERPRINT,
        cursor=CURSOR_CODEC.decode(cursor, FINGERPRINT) if cursor else None,
        raw_cursor=cursor,
    )


def test_first_page_is_newest_first():
    page = keyset_slice(rows(5), page_request(limit=2))

    assert [row.id for row in page[:2]] == ["r0", "r1"]


def test_walking_covers_every_row_exactly_once():
    everything = rows(5)
    seen: list[str] = []
    request = page_request(limit=2)

    while True:
        page = build_page(keyset_slice(everything, request), total=5, request=request)
        seen.extend(row.id for row in page.items)
        if page.next_cursor is None:
            break
        request = page_request(limit=2, cursor=page.next_cursor)

    assert seen == ["r0", "r1", "r2", "r3", "r4"]


def test_a_row_added_at_the_head_cannot_shift_a_page():
    everything = rows(4)
    first_request = page_request(limit=2)
    first = build_page(keyset_slice(everything, first_request), total=4, request=first_request)

    everything.append(Row(id="newest", created_at=START + timedelta(days=1)))

    second_request = page_request(limit=2, cursor=first.next_cursor)
    second = build_page(keyset_slice(everything, second_request), total=5, request=second_request)

    assert [row.id for row in second.items] == ["r2", "r3"]


def test_paging_backwards_returns_the_previous_page_in_reading_order():
    everything = rows(4)

    first_request = page_request(limit=2)
    first = build_page(keyset_slice(everything, first_request), total=4, request=first_request)

    second_request = page_request(limit=2, cursor=first.next_cursor)
    second = build_page(keyset_slice(everything, second_request), total=4, request=second_request)

    back_request = page_request(limit=2, cursor=second.previous_cursor)
    back = build_page(keyset_slice(everything, back_request), total=4, request=back_request)

    assert [row.id for row in back.items] == ["r0", "r1"]


def test_cursor_resolves_after_its_anchor_row_is_gone():
    everything = rows(4)
    first_request = page_request(limit=2)
    first = build_page(keyset_slice(everything, first_request), total=4, request=first_request)

    everything = [row for row in everything if row.id != "r1"]

    second_request = page_request(limit=2, cursor=first.next_cursor)
    second = build_page(keyset_slice(everything, second_request), total=3, request=second_request)

    assert [row.id for row in second.items] == ["r2", "r3"]


def test_rows_sharing_a_timestamp_are_separated_by_id():
    same_moment = [Row(id=f"r{index}", created_at=START) for index in range(3)]

    page = keyset_slice(same_moment, page_request(limit=3))

    assert [row.id for row in page] == ["r2", "r1", "r0"]

"""Keyset paging against a real Postgres, which is the only place the predicate
and the index have to agree."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from data_read_core.shared.pagination import (
    CREATED_AT_DESC,
    PageRequest,
    apply_keyset,
    build_page,
)
from data_read_core.shared.postgres_orm import TransactionReadModel

pytestmark = pytest.mark.django_db(transaction=True)

FACTORY = APIRequestFactory()
START = datetime(2026, 1, 1, tzinfo=UTC)
USER_ID = 7002


def page_request(limit: int, cursor: str | None = None) -> PageRequest:
    query = {"limit": str(limit)}
    if cursor:
        query["cursor"] = cursor

    return PageRequest.from_request(
        Request(FACTORY.get("/transactions", query)),
        CREATED_AT_DESC,
    )


async def make_transactions(count: int) -> list[TransactionReadModel]:
    return [
        await TransactionReadModel.objects.acreate(
            id=uuid4(),
            wallet_id=uuid4(),
            user_id=USER_ID,
            amount=Decimal("1.00"),
            currency_code="USD",
            occurred_at=START - timedelta(days=index),
            created_at=START - timedelta(days=index),
        )
        for index in range(count)
    ]


async def read_page(request: PageRequest) -> list[TransactionReadModel]:
    queryset = apply_keyset(TransactionReadModel.objects.filter(user_id=USER_ID), request)

    return [row async for row in queryset]


async def test_walking_pages_covers_every_row_exactly_once():
    created = await make_transactions(5)
    expected = [str(row.id) for row in created]

    seen: list[str] = []
    request = page_request(limit=2)

    while True:
        page = build_page(await read_page(request), total=len(created), request=request)
        seen.extend(str(row.id) for row in page.items)
        if page.next_cursor is None:
            break
        request = page_request(limit=2, cursor=page.next_cursor)

    assert seen == expected


async def test_a_row_inserted_at_the_head_cannot_shift_a_page():
    """The failure offset has: insert while paging, and offset=25 re-serves a
    row the client already saw."""

    created = await make_transactions(4)
    first_request = page_request(limit=2)
    first = build_page(await read_page(first_request), total=4, request=first_request)

    await make_transactions(1)  # newest row, lands at the head of the collection

    second_request = page_request(limit=2, cursor=first.next_cursor)
    second = build_page(await read_page(second_request), total=5, request=second_request)

    assert [str(row.id) for row in first.items] == [str(row.id) for row in created[:2]]
    assert [str(row.id) for row in second.items] == [str(row.id) for row in created[2:4]]


async def test_paging_backwards_returns_the_previous_page_in_reading_order():
    created = await make_transactions(4)

    first_request = page_request(limit=2)
    first = build_page(await read_page(first_request), total=4, request=first_request)

    second_request = page_request(limit=2, cursor=first.next_cursor)
    second = build_page(await read_page(second_request), total=4, request=second_request)

    back_request = page_request(limit=2, cursor=second.previous_cursor)
    back = build_page(await read_page(back_request), total=4, request=back_request)

    assert [str(row.id) for row in back.items] == [str(row.id) for row in created[:2]]


async def test_cursor_resolves_after_its_anchor_row_is_deleted():
    """A cursor describes a position in the ordering, not a row that must still
    exist."""

    created = await make_transactions(4)
    first_request = page_request(limit=2)
    first = build_page(await read_page(first_request), total=4, request=first_request)

    await TransactionReadModel.objects.filter(id=created[1].id).adelete()

    second_request = page_request(limit=2, cursor=first.next_cursor)
    second = build_page(await read_page(second_request), total=3, request=second_request)

    assert [str(row.id) for row in second.items] == [str(row.id) for row in created[2:4]]

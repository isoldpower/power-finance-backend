from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from data_read_core.query_slices.search_wallets.dtos import SearchWalletsQuery
from data_read_core.query_slices.search_wallets.query_handler import (
    SearchWalletsQueryHandler,
)
from data_read_core.shared.pagination import (
    FAVORITE_CREATED_AT_DESC,
    PageRequest,
    query_fingerprint,
)

pytestmark = pytest.mark.django_db(transaction=True)

EXTERNAL_USER_ID = "user_search_wallets"
JULY = datetime(2026, 7, 15, 12, tzinfo=UTC)

ELASTICSEARCH_SEARCH_FUNCTION = (
    "data_read_core.query_slices.search_wallets.query_handler.search_owned_wallets"
)
ANY_WALLET_FILTER = {"field_name": "currency", "operator": "eq", "value": "USD"}


async def _user_id() -> int:
    user, _ = await get_user_model().objects.aget_or_create(username=EXTERNAL_USER_ID)
    return user.id


def _elasticsearch_document(*, balance: float, zero_balance: float) -> dict:
    return {
        "id": "7e8244e4-4b7d-4833-8219-d256efd206cc",
        "user_id": 1,
        "title": "Main",
        "currency_code": "USD",
        "balance": balance,
        "zero_balance": zero_balance,
        "created_at": JULY.isoformat(),
        "updated_at": None,
        "deleted_at": None,
        "category": "",
        "color": "",
        "favorite": False,
    }


async def _search_query() -> SearchWalletsQuery:
    return SearchWalletsQuery(
        user_id=await _user_id(),
        filter_body=ANY_WALLET_FILTER,
        page=PageRequest(
            limit=25,
            order=FAVORITE_CREATED_AT_DESC,
            fingerprint=query_fingerprint(FAVORITE_CREATED_AT_DESC),
        ),
    )


async def test_the_indexed_balance_is_what_gets_served():
    matched_documents = [_elasticsearch_document(balance=9500.0, zero_balance=25.0)]

    with patch(ELASTICSEARCH_SEARCH_FUNCTION, return_value=(matched_documents, 1)):
        result = await SearchWalletsQueryHandler().handle(await _search_query())

    assert [row.balance_amount for row in result.rows] == ["9500.0"]
    assert [row.zero_balance_amount for row in result.rows] == ["25.0"]
    assert result.total == 1


async def test_a_document_missing_its_balance_reads_as_zero():
    document = _elasticsearch_document(balance=0.0, zero_balance=0.0)
    del document["balance"]
    del document["zero_balance"]

    with patch(ELASTICSEARCH_SEARCH_FUNCTION, return_value=([document], 1)):
        result = await SearchWalletsQueryHandler().handle(await _search_query())

    assert [row.balance_amount for row in result.rows] == ["0"]

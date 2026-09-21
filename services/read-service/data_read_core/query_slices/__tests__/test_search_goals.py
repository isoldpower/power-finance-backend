import json
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import AsyncClient

from data_read_core.query_slices.search_goals.dtos import SearchGoalsQuery
from data_read_core.query_slices.search_goals.query_handler import SearchGoalsQueryHandler
from data_read_core.shared.pagination import (
    CREATED_AT_DESC,
    PageRequest,
    query_fingerprint,
)

pytestmark = pytest.mark.django_db(transaction=True)

EXTERNAL_USER_ID = "user_search_goals"
AUTH_HEADERS = {"X-User-Id": EXTERNAL_USER_ID}
GOALS_SEARCH = "/api/v1/goals/search"
MARCH = datetime(2026, 3, 12, 9, tzinfo=UTC)
DECEMBER = datetime(2026, 12, 31, tzinfo=UTC)

ELASTICSEARCH_SEARCH_FUNCTION = (
    "data_read_core.query_slices.search_goals.query_handler.search_owned_goals"
)
ANY_GOAL_FILTER = {"field_name": "currency", "operator": "eq", "value": "USD"}


@pytest.fixture(autouse=True)
async def _provisioned():
    await get_user_model().objects.acreate(username=EXTERNAL_USER_ID)


async def _user_id() -> int:
    user = await get_user_model().objects.aget(username=EXTERNAL_USER_ID)
    return user.id


def _elasticsearch_document(*, target: float = 1200.0, progress: float = 450.0) -> dict:
    return {
        "id": "6d1b2f44-9c3e-4a71-8f52-77c0f1a0b311",
        "user_id": 1,
        "title": "New laptop",
        "currency_code": "USD",
        "target": target,
        "progress": progress,
        "url": None,
        "finish_at": DECEMBER.isoformat(),
        "created_at": MARCH.isoformat(),
        "updated_at": None,
        "deleted_at": None,
    }


async def _search_query(filter_body: dict) -> SearchGoalsQuery:
    return SearchGoalsQuery(
        user_id=await _user_id(),
        filter_body=filter_body,
        page=PageRequest(
            limit=25,
            order=CREATED_AT_DESC,
            fingerprint=query_fingerprint(CREATED_AT_DESC),
        ),
    )


async def _post(filter_body: dict):
    return await AsyncClient().post(
        GOALS_SEARCH,
        data=json.dumps({"filter_body": filter_body}),
        content_type="application/json",
        headers=AUTH_HEADERS,
    )


async def test_the_indexed_target_and_progress_are_what_get_served():
    matched_documents = [_elasticsearch_document()]

    with patch(ELASTICSEARCH_SEARCH_FUNCTION, return_value=(matched_documents, 1)):
        result = await SearchGoalsQueryHandler().handle(await _search_query(ANY_GOAL_FILTER))

    assert [row.target_amount for row in result.rows] == ["1200.0"]
    assert [row.progress_amount for row in result.rows] == ["450.0"]
    assert result.total == 1


async def test_a_document_missing_its_money_reads_as_zero():
    document = _elasticsearch_document()
    del document["target"]
    del document["progress"]

    with patch(ELASTICSEARCH_SEARCH_FUNCTION, return_value=([document], 1)):
        result = await SearchGoalsQueryHandler().handle(await _search_query(ANY_GOAL_FILTER))

    assert [row.target_amount for row in result.rows] == ["0"]
    assert [row.progress_amount for row in result.rows] == ["0"]


async def test_the_endpoint_presents_both_amounts_as_money():
    with patch(ELASTICSEARCH_SEARCH_FUNCTION, return_value=([_elasticsearch_document()], 1)):
        response = await _post(ANY_GOAL_FILTER)

    row = json.loads(response.content)["data"][0]

    assert row["name"] == "New laptop"
    assert row["currency"] == "USD"
    assert row["target"]["amount"] == "1200.00"
    assert row["progress"]["amount"] == "450.00"


async def test_the_search_refuses_the_stored_column_name():
    response = await _post({"field_name": "title", "operator": "eq", "value": "New laptop"})

    assert response.status_code == 422


async def test_progress_is_filterable_so_a_client_can_ask_for_unfinished_goals():
    with patch(ELASTICSEARCH_SEARCH_FUNCTION, return_value=([_elasticsearch_document()], 1)):
        response = await _post({"field_name": "progress", "operator": "lt", "value": "1200.00"})

    assert response.status_code == 200
    assert json.loads(response.content)["data"][0]["name"] == "New laptop"

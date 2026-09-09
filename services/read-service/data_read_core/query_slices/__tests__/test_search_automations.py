import json
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import AsyncClient

from data_read_core.query_slices.search_automations.dtos import SearchAutomationsQuery
from data_read_core.query_slices.search_automations.query_handler import (
    SearchAutomationsQueryHandler,
)
from data_read_core.shared.pagination import (
    CREATED_AT_DESC,
    PageRequest,
    query_fingerprint,
)

pytestmark = pytest.mark.django_db(transaction=True)

EXTERNAL_USER_ID = "user_search_automations"
AUTH_HEADERS = {"X-User-Id": EXTERNAL_USER_ID}
AUTOMATIONS_SEARCH = "/api/v1/automations/search"
FEBRUARY = datetime(2026, 2, 10, 12, tzinfo=UTC)

ELASTICSEARCH_SEARCH_FUNCTION = (
    "data_read_core.query_slices.search_automations.query_handler.search_owned_automations"
)
COFFEE_FILTER = {"and": [{"field_name": "name", "operator": "icontains", "value": "coffee"}]}
ENABLED_RULES_FILTER = {"field_name": "enabled", "operator": "eq", "value": True}


@pytest.fixture(autouse=True)
async def _provisioned():
    await get_user_model().objects.acreate(username=EXTERNAL_USER_ID)


async def _user_id() -> int:
    user = await get_user_model().objects.aget(username=EXTERNAL_USER_ID)
    return user.id


def _elasticsearch_document(
    *,
    name: str = "Auto-categorise coffee shops",
    enabled: bool = True,
    runs: int = 3,
) -> dict:
    return {
        "id": "1c0f2a3e-8a3e-4c11-9d2b-3f0d9f6b1c77",
        "user_id": 1,
        "name": name,
        "icon": "tag",
        "enabled": enabled,
        "trigger_type": "event",
        "trigger_event": "transaction.created",
        "trigger_schedule": "",
        "filter_body": COFFEE_FILTER,
        "effects": [{"type": "set_category", "params": {"category": "Dining"}}],
        "runs": runs,
        "last_run_at": FEBRUARY.isoformat(),
        "created_at": FEBRUARY.isoformat(),
        "updated_at": None,
        "deleted_at": None,
    }


async def _search_query(filter_body: dict) -> SearchAutomationsQuery:
    return SearchAutomationsQuery(
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
        AUTOMATIONS_SEARCH,
        data=json.dumps({"filter_body": filter_body}),
        content_type="application/json",
        headers=AUTH_HEADERS,
    )


async def test_the_indexed_rule_is_what_gets_served():
    matched_documents = [_elasticsearch_document()]

    with patch(ELASTICSEARCH_SEARCH_FUNCTION, return_value=(matched_documents, 1)):
        result = await SearchAutomationsQueryHandler().handle(
            await _search_query(ENABLED_RULES_FILTER)
        )

    assert [row.name for row in result.rows] == ["Auto-categorise coffee shops"]
    assert [row.runs for row in result.rows] == [3]
    assert result.total == 1


async def test_a_document_missing_its_run_count_reads_as_never_run():
    document = _elasticsearch_document()
    del document["runs"]
    del document["last_run_at"]

    with patch(ELASTICSEARCH_SEARCH_FUNCTION, return_value=([document], 1)):
        result = await SearchAutomationsQueryHandler().handle(
            await _search_query(ENABLED_RULES_FILTER)
        )

    assert [row.runs for row in result.rows] == [0]
    assert [row.last_run_at for row in result.rows] == [None]


async def test_the_endpoint_presents_the_trigger_as_a_nested_object():
    with patch(ELASTICSEARCH_SEARCH_FUNCTION, return_value=([_elasticsearch_document()], 1)):
        response = await _post(ENABLED_RULES_FILTER)

    row = json.loads(response.content)["data"][0]

    assert row["trigger"] == {
        "type": "event",
        "event": "transaction.created",
        "schedule": None,
        "filter_body": COFFEE_FILTER,
    }
    assert row["effects"] == [{"type": "set_category", "params": {"category": "Dining"}}]


async def test_the_search_refuses_a_field_the_rules_do_not_expose():
    response = await _post({"field_name": "effects", "operator": "eq", "value": "notify"})

    assert response.status_code == 422


async def test_a_scheduled_rule_is_reachable_by_its_cadence():
    document = _elasticsearch_document(name="Weekly savings sweep")
    document["trigger_type"] = "schedule"
    document["trigger_event"] = ""
    document["trigger_schedule"] = "weekly"

    with patch(ELASTICSEARCH_SEARCH_FUNCTION, return_value=([document], 1)) as searched:
        response = await _post(
            {"field_name": "trigger_schedule", "operator": "eq", "value": "weekly"}
        )

    row = json.loads(response.content)["data"][0]

    assert searched.called
    assert row["trigger"]["schedule"] == "weekly"
    assert row["trigger"]["event"] is None

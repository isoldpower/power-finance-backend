"""The conversation's REST edge: reading the history and clearing it."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from service_core.shared.db_connection import get_session_factory
from service_core.shared.http_contract import ApiError, error_response

from .. import build_assistant_router
from ..contracts import (
    ConversationMessage,
    MessageRole,
    MessageStatus,
    ResourceReference,
)
from ..infrastructure import SqlAlchemyMessageRepository

AUTHENTICATED = {"X-User-Id": "clerk_7"}
STRANGER = {"X-User-Id": "clerk_9"}
MESSAGES = "/api/v1/assistant/messages"
NOON = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()

    @app.exception_handler(ApiError)
    async def handle(request: Request, failure: ApiError) -> JSONResponse:
        return error_response(request, failure)

    app.include_router(
        build_assistant_router(SqlAlchemyMessageRepository(get_session_factory())),
        prefix="/api/v1",
    )

    return TestClient(app)


async def _seed(owner: str, count: int) -> None:
    store = SqlAlchemyMessageRepository(get_session_factory())
    for index in range(count):
        await store.append(
            owner,
            ConversationMessage(
                id=uuid4(),
                role=MessageRole.USER if index % 2 == 0 else MessageRole.ASSISTANT,
                status=MessageStatus.COMPLETE,
                text=f"message {index}",
                created_at=NOON + timedelta(minutes=index),
            ),
        )


async def test_the_history_is_served_newest_first(client):
    await _seed("clerk_7", 3)

    body = client.get(MESSAGES, headers=AUTHENTICATED).json()

    assert [row["text"] for row in body["data"]] == ["message 2", "message 1", "message 0"]
    assert body["meta"]["total"] == 3


async def test_a_message_carries_the_documented_shape(client):
    store = SqlAlchemyMessageRepository(get_session_factory())
    await store.append(
        "clerk_7",
        ConversationMessage(
            id=uuid4(),
            role=MessageRole.ASSISTANT,
            status=MessageStatus.COMPLETE,
            text="You spent 412.30 USD",
            created_at=NOON,
            refs=(ResourceReference(type="transaction", id=uuid4()),),
        ),
    )

    row = client.get(MESSAGES, headers=AUTHENTICATED).json()["data"][0]

    assert set(row) == {"id", "created_at", "role", "status", "text", "refs"}
    assert row["role"] == "assistant"
    assert row["status"] == "complete"
    assert row["refs"][0]["type"] == "transaction"


async def test_refs_are_an_empty_array_rather_than_null(client):
    """`[]`, never `null`, and never absent."""

    await _seed("clerk_7", 1)

    assert client.get(MESSAGES, headers=AUTHENTICATED).json()["data"][0]["refs"] == []


async def test_an_empty_conversation_is_an_empty_page(client):
    body = client.get(MESSAGES, headers=AUTHENTICATED).json()

    assert body["data"] == []
    assert body["meta"] == {
        "limit": 25,
        "total": 0,
        "next_cursor": None,
        "prev_cursor": None,
    }


async def test_the_page_walks_forward_and_back(client):
    await _seed("clerk_7", 5)

    first = client.get(f"{MESSAGES}?limit=2", headers=AUTHENTICATED).json()
    assert [row["text"] for row in first["data"]] == ["message 4", "message 3"]

    second = client.get(
        f"{MESSAGES}?limit=2&cursor={first['meta']['next_cursor']}",
        headers=AUTHENTICATED,
    ).json()
    assert [row["text"] for row in second["data"]] == ["message 2", "message 1"]

    back = client.get(
        f"{MESSAGES}?limit=2&cursor={second['meta']['prev_cursor']}",
        headers=AUTHENTICATED,
    ).json()
    assert [row["text"] for row in back["data"]] == ["message 4", "message 3"]


async def test_an_unreadable_cursor_is_refused(client):
    response = client.get(f"{MESSAGES}?cursor=not-a-cursor", headers=AUTHENTICATED)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "cursor_invalid"


async def test_one_users_conversation_is_not_another_users(client):
    await _seed("clerk_7", 2)

    assert client.get(MESSAGES, headers=STRANGER).json()["data"] == []


async def test_a_request_that_did_not_pass_the_gateway_is_refused(client):
    response = client.get(MESSAGES)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_clearing_reports_a_count(client):
    await _seed("clerk_7", 4)

    body = client.delete(MESSAGES, headers=AUTHENTICATED).json()

    assert body == {"data": {"deleted": 4}, "meta": {}}
    assert client.get(MESSAGES, headers=AUTHENTICATED).json()["data"] == []


async def test_clearing_an_empty_conversation_succeeds(client):
    response = client.delete(MESSAGES, headers=AUTHENTICATED)

    assert response.status_code == 200
    assert response.json()["data"] == {"deleted": 0}


async def test_clearing_does_not_reach_another_conversation(client):
    await _seed("clerk_7", 2)
    await _seed("clerk_9", 3)

    client.delete(MESSAGES, headers=AUTHENTICATED)

    assert client.get(MESSAGES, headers=STRANGER).json()["meta"]["total"] == 3


async def test_an_oversized_limit_is_clamped_rather_than_refused(client):
    """Every other collection in this API caps at 100 and serves the page. A
    422 here would be this one endpoint disagreeing with the convention."""

    await _seed("clerk_7", 3)

    response = client.get(f"{MESSAGES}?limit=5000", headers=AUTHENTICATED)

    assert response.status_code == 200
    assert response.json()["meta"]["limit"] == 100


async def test_a_limit_that_is_not_a_number_is_refused_in_the_envelope(client):
    response = client.get(f"{MESSAGES}?limit=plenty", headers=AUTHENTICATED)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_failed"
    assert body["error"]["details"][0]["field"] == "limit"

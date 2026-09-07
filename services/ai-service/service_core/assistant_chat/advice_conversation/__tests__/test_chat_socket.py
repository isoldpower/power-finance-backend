import pathlib
import threading

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from .. import GATEWAY_USER_HEADER, TerminationReason, build_chat_router
from .fakes import InMemoryMessageRepository

AUTHENTICATED = {GATEWAY_USER_HEADER: "clerk_7"}

REPOSITORY = pathlib.Path(__file__).resolve().parents[6]
CLERK_PLUGIN = REPOSITORY / "infrastructure" / "kong" / "plugins" / "clerk-jwt" / "handler.lua"


def _client(messages: InMemoryMessageRepository | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(
        build_chat_router(messages=messages or InMemoryMessageRepository()),
        prefix="/api/v1",
    )

    return TestClient(app)


def test_a_socket_carrying_the_gateway_identity_is_served():
    with _client().websocket_connect("/api/v1/chat/advice", headers=AUTHENTICATED) as socket:
        socket.send_json({"text": "Why is my dining spend up?"})

        assert socket.receive_json()["event"] == "accepted"


def test_the_reply_arrives_as_the_target_event_vocabulary():
    with _client().websocket_connect("/api/v1/chat/advice", headers=AUTHENTICATED) as socket:
        socket.send_json({"text": "hello"})

        events = []
        while True:
            frame = socket.receive_json()
            events.append(frame["event"])
            if frame["event"] in {"message", "error"}:
                break

    assert events[0] == "accepted"
    assert events[-1] == "message"
    assert "delta" in events


def test_the_deltas_concatenate_into_the_authoritative_text():
    with _client().websocket_connect("/api/v1/chat/advice", headers=AUTHENTICATED) as socket:
        socket.send_json({"text": "hello"})

        accumulated = ""
        while True:
            frame = socket.receive_json()
            if frame["event"] == "delta":
                accumulated += frame["data"]["text"]
            if frame["event"] == "message":
                final = frame["data"]
                break

    assert accumulated == final["text"]
    assert final["text"] == "Received message: hello"


def test_both_ids_arrive_before_any_text():
    store = InMemoryMessageRepository()

    with _client(store).websocket_connect("/api/v1/chat/advice", headers=AUTHENTICATED) as socket:
        socket.send_json({"text": "hello"})
        accepted = socket.receive_json()

    assert accepted["event"] == "accepted"
    assert set(accepted["data"]) == {"user_message_id", "message_id"}

    stored = {str(message.id) for message in store.stored()}
    assert stored == {accepted["data"]["user_message_id"], accepted["data"]["message_id"]}


def test_a_socket_without_the_gateway_identity_is_closed():
    with pytest.raises(WebSocketDisconnect) as refusal:
        _client().websocket_connect("/api/v1/chat/advice").__enter__()

    assert refusal.value.code == TerminationReason.POLICY_VIOLATION.value


def test_an_empty_gateway_identity_is_refused_too():
    with pytest.raises(WebSocketDisconnect) as refusal:
        _client().websocket_connect(
            "/api/v1/chat/advice",
            headers={GATEWAY_USER_HEADER: ""},
        ).__enter__()

    assert refusal.value.code == TerminationReason.POLICY_VIOLATION.value


def test_the_header_is_the_one_the_gateway_plugin_sets():
    plugin = CLERK_PLUGIN.read_text()

    assert f'set_header("{GATEWAY_USER_HEADER}"' in plugin


def _close_code_after(message: dict, timeout: float = 5.0) -> int:
    outcome: list[int] = []

    def attempt() -> None:
        with (
            pytest.raises(WebSocketDisconnect) as closed,
            _client().websocket_connect("/api/v1/chat/advice", headers=AUTHENTICATED) as socket,
        ):
            socket.send_json(message)
            socket.receive_text()

        outcome.append(closed.value.code)

    attempting = threading.Thread(target=attempt, daemon=True)
    attempting.start()
    attempting.join(timeout)

    assert outcome, f"the socket did not close within {timeout}s"

    return outcome[0]


def test_a_message_no_handler_claims_closes_the_socket_with_a_readable_code():
    assert _close_code_after({"nothing": "claims this"}) == (
        TerminationReason.UNSUPPORTED_DATA.value
    )

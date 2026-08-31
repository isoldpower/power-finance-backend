"""The chat socket, and who is allowed to open one.

ai-service is reachable only through Kong, whose `clerk-jwt` plugin sets
`X-User-Id`. These assertions are what stops the socket from serving a caller
that never passed the gateway.
"""

import pathlib
import threading

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from .. import GATEWAY_USER_HEADER, TerminationReason, build_chat_router

AUTHENTICATED = {GATEWAY_USER_HEADER: "clerk_7"}

REPOSITORY = pathlib.Path(__file__).resolve().parents[6]
CLERK_PLUGIN = REPOSITORY / "infrastructure" / "kong" / "plugins" / "clerk-jwt" / "handler.lua"


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(build_chat_router(), prefix="/api/v1")

    return TestClient(app)


def test_a_socket_carrying_the_gateway_identity_is_served():
    with _client().websocket_connect("/api/v1/chat/advice", headers=AUTHENTICATED) as socket:
        socket.send_json({"name": "Nikita"})

        assert socket.receive_text() == "Hello, Nikita"


def test_a_socket_without_the_gateway_identity_is_closed():
    """A handshake that reached this service without `X-User-Id` did not come
    through Kong. Serving it would mean answering an unauthenticated caller."""

    with pytest.raises(WebSocketDisconnect) as refusal:
        _client().websocket_connect("/api/v1/chat/advice").__enter__()

    assert refusal.value.code == TerminationReason.POLICY_VIOLATION.value


def test_an_empty_gateway_identity_is_refused_too():
    """`clerk-jwt` rejects a token with a blank `sub`, but a header set to the
    empty string by anything else must not read as a valid user."""

    with pytest.raises(WebSocketDisconnect) as refusal:
        _client().websocket_connect(
            "/api/v1/chat/advice",
            headers={GATEWAY_USER_HEADER: ""},
        ).__enter__()

    assert refusal.value.code == TerminationReason.POLICY_VIOLATION.value


def test_the_header_is_the_one_the_gateway_plugin_sets():
    """Both sides of this were written here, so a test that used the constant
    for the app and the request too would pass under any spelling. The name is
    not ai-service's to choose: it is whatever `clerk-jwt` sets on the way
    through, and the socket reads nothing else."""

    plugin = CLERK_PLUGIN.read_text()

    assert f'set_header("{GATEWAY_USER_HEADER}"' in plugin


def _close_code_after(message: dict, timeout: float = 5.0) -> int:
    """The code the client is left with after sending one message.

    Run under a timeout, and off the calling thread, because `TestClient`'s
    socket has no deadline of its own: a server that stops terminating would
    leave both ends waiting on each other, and the test would hang rather than
    fail.
    """

    outcome: list[int] = []

    def attempt() -> None:
        with (
            pytest.raises(WebSocketDisconnect) as closed,
            _client().websocket_connect("/api/v1/chat/advice", headers=AUTHENTICATED) as socket,
        ):
            socket.send_json(message)
            socket.receive_text()

        outcome.append(closed.value.code)

    # Daemon, so a socket that never closes cannot hold the interpreter open at
    # exit the way a pooled worker would.
    attempting = threading.Thread(target=attempt, daemon=True)
    attempting.start()
    attempting.join(timeout)

    assert outcome, f"the socket did not close within {timeout}s"

    return outcome[0]


def test_a_message_no_handler_claims_closes_the_socket_with_a_readable_code():
    """The close code has to reach the wire as a number.

    The session's own tests drive a fake transport, so nothing there notices if
    the real one hands Starlette something that is not an int — and every
    announced close would raise instead of closing.
    """

    assert _close_code_after({"nothing": "claims this"}) == (
        TerminationReason.UNSUPPORTED_DATA.value
    )

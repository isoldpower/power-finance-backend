"""What `build_app` decides.

These assertions cross chunks on purpose — assembly is the one place allowed
to — and that is exactly why they live here rather than beside the slice: the
mount prefix and the shutdown wiring are decisions `service_core` does not make
and must not have to import `ai_service` to check.
"""

import pathlib

import yaml
from fastapi.testclient import TestClient
from service_core.assistant_chat import ProcessShutdownSignal

from ..build_app import build_app

REPOSITORY = pathlib.Path(__file__).resolve().parents[4]
KONG_CONFIG = REPOSITORY / "infrastructure" / "kong" / "kong.yml"

AUTHENTICATED = {"X-User-Id": "clerk_7"}


def _kong_chat_prefix() -> str:
    """The path the gateway actually forwards to ai-service."""

    config = yaml.safe_load(KONG_CONFIG.read_text())
    service = next(entry for entry in config["services"] if entry["name"] == "ai-service")
    route = next(entry for entry in service["routes"] if entry["name"] == "assistant-chat")

    return route["paths"][0]


def test_the_socket_is_mounted_under_the_path_kong_routes_here():
    """The gateway route and the app mount live in two files, in two languages,
    and nothing links them. Kong sends `/api/v1/chat` here by a path longer than
    the read route's bare `/api/v1`; if either side moved on its own, the upgrade
    would be offered to read-service, which does not speak it."""

    served = TestClient(build_app())

    with served.websocket_connect(f"{_kong_chat_prefix()}/advice", headers=AUTHENTICATED):
        pass


def test_the_app_hands_the_chat_a_shutdown_signal():
    assert isinstance(build_app().state.chat_shutdown_signal, ProcessShutdownSignal)


def test_the_app_fires_that_signal_when_the_lifespan_ends():
    """Entering and leaving the TestClient context runs startup and shutdown. A
    socket open at that moment has to be told, so the signal the router was
    handed must be the one the lifespan terminates."""

    app = build_app()
    signal = app.state.chat_shutdown_signal

    assert signal.is_terminated() is False

    with TestClient(app):
        assert signal.is_terminated() is False

    assert signal.is_terminated() is True

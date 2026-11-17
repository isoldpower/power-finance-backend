import json
import re
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from django.test import override_settings
from rest_framework.test import APIRequestFactory
from write_service.common.http_contract import Forbidden

from data_write_core.application.commands.demo import DemoSessionDTO
from data_write_core.domain.entities import InternalUserEntity
from data_write_core.infrastructure.demo import HmacDemoVisitCodec
from data_write_core.presentation.http.auth import (
    GatewayUser,
    IsNotGuestDemoAccount,
    UserPreferences,
)
from data_write_core.presentation.http.views.demo import (
    DemoSessionView,
    DemoVisitView,
    demo_session_view,
    demo_visit_view,
)


def _caller(external_id: str) -> GatewayUser:
    return GatewayUser(
        internal=InternalUserEntity(
            user_id="5",
            external_id=external_id,
            email="",
            first_name="",
            last_name="",
        ),
        preferences=UserPreferences(currency="USD", timezone="UTC", language="en"),
    )


def _request(method: str, external_id: str):
    return SimpleNamespace(method=method, user=_caller(external_id))


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_a_guest_demo_account_cannot_change_webhooks(method):
    with pytest.raises(Forbidden):
        IsNotGuestDemoAccount().has_permission(_request(method, "demo_abc123"), view=None)


def test_a_guest_demo_account_can_still_read_webhooks():
    assert IsNotGuestDemoAccount().has_permission(_request("GET", "demo_abc123"), view=None)


def test_a_signed_in_user_can_change_webhooks():
    assert IsNotGuestDemoAccount().has_permission(_request("POST", "user_2abc"), view=None)


DEMO_SETTINGS = {
    "TOKEN_SECRET": "test-demo-secret-that-is-long-enough-0000",
    "TOKEN_ISSUER": "power-finance-demo",
    "TOKEN_TTL_SECONDS": 60,
    "VISIT_SECRET": "test-demo-session-secret-long-enough-00000",
    "VISIT_TTL_SECONDS": 3600,
    "VISIT_ROTATION_SECONDS": 300,
    "VISIT_REDIS_DB": 0,
}


def _issued_visit_identifier() -> str:
    return (
        HmacDemoVisitCodec(
            secret=DEMO_SETTINGS["VISIT_SECRET"],
            lifetime=timedelta(seconds=DEMO_SETTINGS["VISIT_TTL_SECONDS"]),
        )
        .issue()
        .identifier
    )


def _session_request(demo_session: str | None = None):
    headers = {"HTTP_X_DEMO_SESSION": demo_session} if demo_session is not None else {}
    return APIRequestFactory().post("/api/v1/demo/sessions", **headers)


@override_settings(DEMO_SESSIONS={**DEMO_SETTINGS, "TOKEN_SECRET": ""})
async def test_demo_sessions_are_refused_when_no_token_secret_is_configured():
    response = await DemoSessionView.as_view()(_session_request(_issued_visit_identifier()))

    assert response.status_code == 503


@override_settings(DEMO_SESSIONS={**DEMO_SETTINGS, "VISIT_SECRET": ""})
async def test_demo_visits_are_refused_when_no_session_secret_is_configured():
    response = await DemoVisitView.as_view()(APIRequestFactory().post("/api/v1/demo/visits"))

    assert response.status_code == 503
    assert json.loads(response.render().content)["error"]["message"] == (
        "Guest demo sessions are not enabled on this deployment"
    )


class InMemoryVisitRegistry:
    def __init__(self) -> None:
        self.active_visits: dict[str, str] = {}

    async def claim_active_visit(self, client_address, candidate_identifier, hold_until) -> str:
        return self.active_visits.setdefault(client_address, candidate_identifier)

    async def replace_active_visit(self, client_address, identifier, hold_until) -> None:
        self.active_visits[client_address] = identifier


@pytest.fixture
def visit_registry(monkeypatch) -> InMemoryVisitRegistry:
    registry = InMemoryVisitRegistry()
    monkeypatch.setattr(demo_visit_view, "build_visit_registry", lambda: registry)
    return registry


async def _issue_visit_from(client_address: str) -> dict:
    response = await DemoVisitView.as_view()(
        APIRequestFactory().post("/api/v1/demo/visits", HTTP_X_REAL_IP=client_address)
    )
    assert response.status_code == 201
    return json.loads(response.render().content)["data"]


@override_settings(DEMO_SESSIONS=DEMO_SETTINGS)
async def test_one_client_holds_one_active_visit(visit_registry):
    first_visit = await _issue_visit_from("203.0.113.7")
    repeated_visit = await _issue_visit_from("203.0.113.7")
    other_client_visit = await _issue_visit_from("198.51.100.4")

    assert repeated_visit == first_visit
    assert other_client_visit["id"] != first_visit["id"]


@override_settings(DEMO_SESSIONS=DEMO_SETTINGS)
async def test_an_issued_visit_is_a_signed_expiring_identifier(visit_registry):
    response = await DemoVisitView.as_view()(APIRequestFactory().post("/api/v1/demo/visits"))

    issued_visit = json.loads(response.render().content)["data"]
    assert response.status_code == 201
    assert re.fullmatch(r"[A-Za-z0-9_-]{16,64}", issued_visit["id"])
    assert datetime.fromisoformat(issued_visit["expires_at"]).utcoffset() == timedelta(0)


@pytest.mark.parametrize("demo_session", [None, "", "f3b1c2d4-5e6f-4a7b-8c9d-0e1f2a3b4c5d"])
@override_settings(DEMO_SESSIONS=DEMO_SETTINGS)
async def test_a_session_without_a_valid_visit_is_refused(demo_session):
    response = await DemoSessionView.as_view()(_session_request(demo_session))

    assert response.status_code == 401
    assert json.loads(response.render().content)["error"]["code"] == "demo_session_invalid"


class SeededSessionHandler:
    received_commands: list = []

    def __init__(self, token_issuer) -> None:
        pass

    async def handle(self, command) -> DemoSessionDTO:
        SeededSessionHandler.received_commands.append(command)
        return DemoSessionDTO(
            token="signed-token",
            expires_at=datetime(2030, 1, 1, tzinfo=UTC),
            external_id="demo_abc123",
            write_version=913,
        )


class RepeatedSessionHandler(SeededSessionHandler):
    async def handle(self, command) -> DemoSessionDTO:
        seeded_session = await super().handle(command)
        return replace(seeded_session, write_version=None)


@override_settings(DEMO_SESSIONS=DEMO_SETTINGS)
async def test_a_started_session_hands_the_gateway_its_seeded_write_version(monkeypatch):
    SeededSessionHandler.received_commands = []
    monkeypatch.setattr(demo_session_view, "StartDemoSessionCommandHandler", SeededSessionHandler)
    visit_identifier = _issued_visit_identifier()

    response = await DemoSessionView.as_view()(_session_request(visit_identifier))

    assert response.status_code == 201
    assert response.headers["X-Write-Version"] == "913"
    assert response.headers["X-Demo-Subject"] == "demo_abc123"
    assert SeededSessionHandler.received_commands[0].visit.identifier == visit_identifier


@override_settings(DEMO_SESSIONS=DEMO_SETTINGS)
async def test_a_repeated_session_carries_no_write_version(monkeypatch):
    monkeypatch.setattr(demo_session_view, "StartDemoSessionCommandHandler", RepeatedSessionHandler)

    response = await DemoSessionView.as_view()(_session_request(_issued_visit_identifier()))

    assert response.status_code == 201
    assert "X-Write-Version" not in response.headers

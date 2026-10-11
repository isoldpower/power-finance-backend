import uuid
from types import SimpleNamespace

import pytest
from rest_framework.test import APIRequestFactory

from data_write_core.application.commands.actions.resolve_action import ResolvedAction
from data_write_core.domain.entities import InternalUserEntity
from data_write_core.presentation.http.auth import GatewayUser, UserPreferences
from data_write_core.presentation.http.views.actions import action_resolve_view

pytestmark = pytest.mark.django_db(transaction=True)

WRITE_VERSION = 4242


class SignedInCallerAuthentication:
    def authenticate(self, request):
        caller = GatewayUser(
            internal=InternalUserEntity(
                user_id="12",
                external_id="user_resolver",
                email="",
                first_name="",
                last_name="",
            ),
            preferences=UserPreferences(currency="USD", timezone="UTC", language="en"),
        )
        return caller, None

    def authenticate_header(self, request):
        return "Bearer"


def _stub_resolution(monkeypatch, applies: bool) -> None:
    monkeypatch.setattr(
        action_resolve_view.ActionResolveView,
        "authentication_classes",
        [SignedInCallerAuthentication],
    )

    class StubResolveActionCommandHandler:
        async def handle(self, command):
            return ResolvedAction(action=SimpleNamespace(), applies=applies), WRITE_VERSION

    monkeypatch.setattr(
        action_resolve_view,
        "ResolveActionCommandHandler",
        StubResolveActionCommandHandler,
    )
    monkeypatch.setattr(
        action_resolve_view.ActionHttpPresenter,
        "present_one",
        staticmethod(lambda action: {"id": "stubbed"}),
    )


async def _resolve():
    action_id = uuid.uuid4()
    request = APIRequestFactory().post(
        f"/api/v1/actions/{action_id}/resolve",
        {"resolution_id": "dismiss"},
        format="json",
    )

    return await action_resolve_view.ActionResolveView.as_view()(request, action_id=action_id)


@pytest.mark.parametrize("applies", [True, False])
async def test_every_resolution_returns_the_version_the_follow_up_read_must_wait_for(
    monkeypatch, applies
):
    _stub_resolution(monkeypatch, applies=applies)

    response = await _resolve()

    assert response.status_code == 200
    assert response.headers["X-Write-Version"] == str(WRITE_VERSION)

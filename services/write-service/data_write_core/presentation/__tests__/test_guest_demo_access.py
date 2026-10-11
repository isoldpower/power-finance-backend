from types import SimpleNamespace

import pytest
from django.test import override_settings
from rest_framework.test import APIRequestFactory
from write_service.common.http_contract import Forbidden

from data_write_core.domain.entities import InternalUserEntity
from data_write_core.presentation.http.auth import (
    GatewayUser,
    IsNotGuestDemoAccount,
    UserPreferences,
)
from data_write_core.presentation.http.views.demo import DemoSessionView


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


@override_settings(DEMO_SESSIONS={"TOKEN_SECRET": "", "TOKEN_ISSUER": "x", "TOKEN_TTL_SECONDS": 60})
async def test_demo_sessions_are_refused_when_no_secret_is_configured():
    request = APIRequestFactory().post("/api/v1/demo/sessions")

    response = await DemoSessionView.as_view()(request)

    assert response.status_code == 503

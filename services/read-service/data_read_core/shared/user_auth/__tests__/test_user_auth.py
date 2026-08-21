"""Gateway header authentication + permission."""

from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed

from data_read_core.shared.user_auth import (
    GATEWAY_USER_HEADER,
    GatewayUser,
    GatewayUserHeaderAuthentication,
    IsGatewayAuthenticated,
    UserPreferences,
)

DEFAULTS = UserPreferences(currency="USD", timezone="UTC", language="en")


def _request(*, method="GET", headers=None):
    return SimpleNamespace(method=method, headers=headers or {})


def test_header_constant():
    assert GATEWAY_USER_HEADER == "X-User-Id"


def test_permission_allows_a_caller_the_gateway_resolved():
    caller = GatewayUser(internal=SimpleNamespace(id=1, username="ext-1"), preferences=DEFAULTS)
    request = SimpleNamespace(user=caller)

    assert IsGatewayAuthenticated().has_permission(request, view=None) is True


def test_permission_denies_anything_that_merely_claims_to_be_authenticated():
    """The type is the check: something that only answers `is_authenticated`
    never went through the gateway."""

    request = SimpleNamespace(user=SimpleNamespace(is_authenticated=True))

    assert IsGatewayAuthenticated().has_permission(request, view=None) is False


def test_permission_denies_when_user_missing():
    request = SimpleNamespace(user=None)
    assert IsGatewayAuthenticated().has_permission(request, view=None) is False


@pytest.mark.django_db(transaction=True)
async def test_authenticate_options_request_is_skipped():
    result = await GatewayUserHeaderAuthentication().authenticate(_request(method="OPTIONS"))
    assert result is None


@pytest.mark.django_db(transaction=True)
async def test_authenticate_missing_header_raises():
    with pytest.raises(AuthenticationFailed, match=GATEWAY_USER_HEADER):
        await GatewayUserHeaderAuthentication().authenticate(_request(headers={}))


@pytest.mark.django_db(transaction=True)
async def test_authenticate_unprovisioned_user_raises():
    with pytest.raises(AuthenticationFailed, match="not yet provisioned"):
        await GatewayUserHeaderAuthentication().authenticate(
            _request(headers={GATEWAY_USER_HEADER: "ext-unknown"})
        )


@pytest.mark.django_db(transaction=True)
async def test_authenticate_returns_provisioned_user():
    internal_user = await get_user_model().objects.acreate(id=1, username="ext-1")

    caller, auth = await GatewayUserHeaderAuthentication().authenticate(
        _request(headers={GATEWAY_USER_HEADER: "ext-1"})
    )

    assert caller.id == internal_user.id
    assert caller.external_id == "ext-1"
    assert auth is None


@pytest.mark.django_db(transaction=True)
async def test_authenticate_binds_preferences_to_the_caller():
    """Identity and preferences arrive on the same request and are needed
    together, so a handler reads both off `request.user`."""

    await get_user_model().objects.acreate(id=2, username="ext-2")

    caller, _ = await GatewayUserHeaderAuthentication().authenticate(
        _request(
            headers={
                GATEWAY_USER_HEADER: "ext-2",
                "X-User-Timezone": "Europe/Berlin",
                "X-User-Language": "de-DE",
            }
        )
    )

    assert caller.preferences.timezone == "Europe/Berlin"
    assert caller.preferences.language == "de-DE"


@pytest.mark.django_db(transaction=True)
async def test_a_caller_without_preferences_gets_the_documented_defaults():
    await get_user_model().objects.acreate(id=3, username="ext-3")

    caller, _ = await GatewayUserHeaderAuthentication().authenticate(
        _request(headers={GATEWAY_USER_HEADER: "ext-3"})
    )

    assert caller.preferences == DEFAULTS

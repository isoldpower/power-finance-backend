"""Gateway header authentication + permission."""

from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed

from data_read_core.shared.user_auth import (
    GATEWAY_USER_HEADER,
    GatewayUserHeaderAuthentication,
    IsGatewayAuthenticated,
)


def _request(*, method="GET", headers=None):
    return SimpleNamespace(method=method, headers=headers or {})


# --------------------------------------------------------------------------- #
# Permission
# --------------------------------------------------------------------------- #
def test_header_constant():
    assert GATEWAY_USER_HEADER == "X-User-Id"


def test_permission_allows_authenticated_user():
    request = SimpleNamespace(user=SimpleNamespace(is_authenticated=True))
    assert IsGatewayAuthenticated().has_permission(request, view=None) is True


def test_permission_denies_anonymous():
    request = SimpleNamespace(user=SimpleNamespace(is_authenticated=False))
    assert IsGatewayAuthenticated().has_permission(request, view=None) is False


def test_permission_denies_when_user_missing():
    request = SimpleNamespace(user=None)
    assert IsGatewayAuthenticated().has_permission(request, view=None) is False


# --------------------------------------------------------------------------- #
# Authentication (DB-backed user lookup)
# --------------------------------------------------------------------------- #
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
    await get_user_model().objects.acreate(id=1, username="ext-1")

    user, auth = await GatewayUserHeaderAuthentication().authenticate(
        _request(headers={GATEWAY_USER_HEADER: "ext-1"})
    )

    assert user.username == "ext-1"
    assert auth is None

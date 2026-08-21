"""The caller a handler sees: identity and preferences bound together."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from rest_framework.exceptions import AuthenticationFailed

from data_write_core.domain.entities import InternalUserEntity
from data_write_core.presentation.http.auth import (
    GATEWAY_USER_HEADER,
    GatewayUser,
    GatewayUserHeaderAuthentication,
    IsGatewayAuthenticated,
    UserPreferences,
)

DEFAULTS = UserPreferences(currency="USD", timezone="UTC", language="en")
SCALES = {"USD": 2, "EUR": 2}


def internal_user() -> InternalUserEntity:
    return InternalUserEntity(
        user_id="7",
        external_id="ext-1",
        email="user@example.com",
        first_name="Test",
        last_name="User",
    )


def request_with(**headers) -> SimpleNamespace:
    return SimpleNamespace(method="GET", headers=headers)


@pytest.fixture
def authentication():
    registry = SimpleNamespace(
        user_repository=SimpleNamespace(
            get_synced_internal=_return(internal_user()),
        )
    )

    with (
        patch(
            "data_write_core.presentation.http.auth.gateway_authentication.get_repository_registry",
            return_value=registry,
        ),
        # `preferences` binds the function at import time, so the patch has to
        # land on its module, not on the one that defines it.
        patch(
            "data_write_core.presentation.http.auth.preferences.load_scales",
            return_value=SCALES,
        ),
    ):
        yield GatewayUserHeaderAuthentication()


def _return(value):
    async def call(**_kwargs):
        return value

    return call


def test_permission_allows_a_caller_the_gateway_resolved():
    caller = GatewayUser(internal=internal_user(), preferences=DEFAULTS)

    assert IsGatewayAuthenticated().has_permission(SimpleNamespace(user=caller), view=None) is True


def test_permission_denies_a_bare_domain_entity():
    """The wrapper is the check. An entity loaded outside a request has no
    preferences and never came through the gateway."""

    request = SimpleNamespace(user=internal_user())

    assert IsGatewayAuthenticated().has_permission(request, view=None) is False


def test_caller_exposes_the_ids_the_handlers_use():
    caller = GatewayUser(internal=internal_user(), preferences=DEFAULTS)

    assert caller.unique_id == "7"
    assert caller.external_id == "ext-1"


async def test_authenticate_binds_preferences_to_the_caller(authentication):
    caller, auth = await authentication.authenticate(
        request_with(
            **{
                GATEWAY_USER_HEADER: "ext-1",
                "X-User-Currency": "EUR",
                "X-User-Timezone": "Europe/Berlin",
            }
        )
    )

    assert auth is None
    assert caller.unique_id == "7"
    assert caller.preferences.currency == "EUR"
    assert caller.preferences.timezone == "Europe/Berlin"


async def test_a_caller_without_preferences_gets_the_documented_defaults(authentication):
    caller, _ = await authentication.authenticate(request_with(**{GATEWAY_USER_HEADER: "ext-1"}))

    assert caller.preferences == DEFAULTS


async def test_a_forged_currency_cannot_pick_its_own_reporting_currency(authentication):
    """`unsafeMetadata` is client-writable, so a bad preference degrades
    presentation rather than failing the request."""

    caller, _ = await authentication.authenticate(
        request_with(**{GATEWAY_USER_HEADER: "ext-1", "X-User-Currency": "XYZ"})
    )

    assert caller.preferences.currency == "USD"


async def test_a_request_that_skipped_the_gateway_is_rejected(authentication):
    with pytest.raises(AuthenticationFailed, match=GATEWAY_USER_HEADER):
        await authentication.authenticate(request_with())


async def test_preflight_requests_are_not_authenticated(authentication):
    request = SimpleNamespace(method="OPTIONS", headers={})

    assert await authentication.authenticate(request) is None

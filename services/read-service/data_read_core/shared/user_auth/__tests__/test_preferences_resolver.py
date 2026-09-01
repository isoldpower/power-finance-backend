import pytest
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from data_read_core.shared.money import CURRENCY_CATALOG
from data_read_core.shared.postgres_orm import CurrencyReadModel
from data_read_core.shared.user_auth import UserPreferences, resolve_preferences

pytestmark = pytest.mark.django_db(transaction=True)

FACTORY = APIRequestFactory()


@pytest.fixture(autouse=True)
async def _reference_currencies():
    CURRENCY_CATALOG.reset()
    await CurrencyReadModel.objects.abulk_create(
        [
            CurrencyReadModel(code="USD", name="US Dollar", numeric="840", digits=2),
            CurrencyReadModel(code="EUR", name="Euro", numeric="978", digits=2),
        ],
        ignore_conflicts=True,
    )
    yield
    CURRENCY_CATALOG.reset()


def request_with(**headers) -> Request:
    return Request(FACTORY.get("/metrics", **headers))


async def test_gateway_supplied_preferences_are_used():
    preferences = await resolve_preferences(
        request_with(
            HTTP_X_USER_CURRENCY="EUR",
            HTTP_X_USER_TIMEZONE="Europe/Berlin",
            HTTP_X_USER_LANGUAGE="de-DE",
        )
    )

    assert preferences == UserPreferences(
        currency="EUR",
        timezone="Europe/Berlin",
        language="de-DE",
    )


async def test_absent_preferences_fall_back_per_field():
    assert await resolve_preferences(request_with()) == UserPreferences(
        currency="USD",
        timezone="UTC",
        language="en",
    )


async def test_an_unsupported_currency_degrades_instead_of_failing():
    """`unsafeMetadata` is client-writable, so a bad preference must degrade
    presentation rather than fail a request."""

    preferences = await resolve_preferences(request_with(HTTP_X_USER_CURRENCY="XYZ"))

    assert preferences.currency == "USD"


@pytest.mark.parametrize("zone", ["Mars/Olympus", "not a zone", "../../etc/passwd"])
async def test_an_unreal_timezone_degrades_to_utc(zone):
    preferences = await resolve_preferences(request_with(HTTP_X_USER_TIMEZONE=zone))

    assert preferences.timezone == "UTC"


async def test_currency_is_case_insensitive():
    preferences = await resolve_preferences(request_with(HTTP_X_USER_CURRENCY="eur"))

    assert preferences.currency == "EUR"


async def test_cache_signature_separates_reporting_currencies():
    """Nothing invalidates on the server when a preference changes, so a cache
    key that ignored the currency would hand a user their old currency back
    under `meta.cached: true`."""

    in_euros = await resolve_preferences(request_with(HTTP_X_USER_CURRENCY="EUR"))
    in_dollars = await resolve_preferences(request_with(HTTP_X_USER_CURRENCY="USD"))

    assert in_euros.cache_signature != in_dollars.cache_signature

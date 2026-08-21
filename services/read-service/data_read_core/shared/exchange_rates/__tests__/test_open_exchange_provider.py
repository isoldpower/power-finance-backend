"""The provider is exercised against a stubbed transport rather than the live
feed: the point is how a payload is read, not whether the internet is up."""

from datetime import timedelta
from decimal import Decimal

import httpx
import pytest

from data_read_core.shared.exchange_rates import OpenExchangeRatesProvider, RateUnavailable

BASE_URL = "https://rates.test/v6/latest"
UPDATED_AT_UNIX = 1755648000


def provider_returning(response: httpx.Response, requested: list[str] | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if requested is not None:
            requested.append(str(request.url))

        return response

    return OpenExchangeRatesProvider(
        BASE_URL,
        timeout_seconds=1.0,
        transport=httpx.MockTransport(handler),
    )


def success_payload(**overrides) -> dict:
    return {
        "result": "success",
        "base_code": "USD",
        "time_last_update_unix": UPDATED_AT_UNIX,
        "rates": {"USD": 1, "EUR": 0.9, "RUB": 81.5},
        **overrides,
    }


async def test_a_successful_payload_becomes_a_snapshot():
    requested: list[str] = []

    snapshot = await provider_returning(
        httpx.Response(200, json=success_payload()),
        requested,
    ).fetch("USD")

    assert requested == [f"{BASE_URL}/USD"]
    assert snapshot.base == "USD"
    assert snapshot.rate_to("RUB") == Decimal("81.5")
    assert snapshot.fetched_at.timestamp() == UPDATED_AT_UNIX


async def test_rates_never_pass_through_a_float():
    """Binary rounding on a rate would show up in the last digits of every
    conversion, so the payload is parsed straight into Decimal."""

    snapshot = await provider_returning(
        httpx.Response(200, text='{"result":"success","rates":{"RUB":81.10}}')
    ).fetch("USD")

    assert snapshot.rate_to("RUB") == Decimal("81.10")


async def test_a_feed_that_refuses_the_base_is_rate_unavailable():
    provider = provider_returning(
        httpx.Response(200, json={"result": "error", "error-type": "unsupported-code"})
    )

    with pytest.raises(RateUnavailable):
        await provider.fetch("XYZ")


async def test_an_http_failure_is_rate_unavailable():
    with pytest.raises(RateUnavailable):
        await provider_returning(httpx.Response(503)).fetch("USD")


async def test_an_unreadable_body_is_rate_unavailable():
    with pytest.raises(RateUnavailable):
        await provider_returning(httpx.Response(200, text="not json")).fetch("USD")


async def test_a_payload_without_rates_is_rate_unavailable():
    provider = provider_returning(httpx.Response(200, json={"result": "success"}))

    with pytest.raises(RateUnavailable):
        await provider.fetch("USD")


async def test_a_feed_that_omits_its_timestamp_is_treated_as_just_published():
    payload = success_payload()
    del payload["time_last_update_unix"]

    snapshot = await provider_returning(httpx.Response(200, json=payload)).fetch("USD")

    assert snapshot.is_fresh(max_age=timedelta(minutes=1))

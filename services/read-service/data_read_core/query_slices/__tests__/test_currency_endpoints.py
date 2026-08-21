"""End of the wire: URL wiring, gateway auth, query-param validation and the
envelope. The handlers themselves are covered by the per-slice tests."""

import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import AsyncClient

from data_read_core.shared.exchange_rates import RateSnapshot, RateUnavailable
from data_read_core.shared.money import CURRENCY_CATALOG
from data_read_core.shared.postgres_orm import CurrencyReadModel

pytestmark = pytest.mark.django_db(transaction=True)

EXTERNAL_USER_ID = "user_2abc"
AUTH_HEADERS = {"X-User-Id": EXTERNAL_USER_ID}


def as_user(path: str):
    """Everything the gateway would have added, minus the gateway."""

    return AsyncClient().get(path, headers=AUTH_HEADERS)


FEED_TIME = datetime(2026, 8, 12, 16, 51, tzinfo=UTC)


class StubRateService:
    def __init__(self, failure: Exception | None = None) -> None:
        self._failure = failure

    async def snapshot_for(self, base_code: str) -> RateSnapshot:
        self._raise_if_configured()

        return RateSnapshot(
            base=base_code,
            rates={"USD": Decimal("1"), "RUB": Decimal("82")},
            fetched_at=FEED_TIME,
        )

    async def rate_between(self, base_code: str, quote_code: str):
        self._raise_if_configured()

        return Decimal("82"), FEED_TIME

    def _raise_if_configured(self) -> None:
        if self._failure is not None:
            raise self._failure


@pytest.fixture
def stub_rates(monkeypatch):
    """Swap the rate service both currency slices build for themselves. Keeps
    the endpoints off Redis and off the feed."""

    def install(service: StubRateService) -> None:
        for module in (
            "data_read_core.query_slices.get_currency_rates.query_handler",
            "data_read_core.query_slices.convert_currency.query_handler",
        ):
            monkeypatch.setattr(f"{module}.get_rate_service", lambda: service)

    return install


@pytest.fixture(autouse=True)
async def _provisioned_user_and_currencies():
    CURRENCY_CATALOG.reset()
    await get_user_model().objects.acreate(username=EXTERNAL_USER_ID)
    await CurrencyReadModel.objects.abulk_create(
        [
            CurrencyReadModel(code="USD", name="US Dollar", symbol="$", numeric="840", digits=2),
            CurrencyReadModel(
                code="RUB", name="Russian Ruble", symbol="₽", numeric="643", digits=2
            ),
        ],
        ignore_conflicts=True,
    )
    yield
    CURRENCY_CATALOG.reset()


def body_of(response) -> dict:
    return json.loads(response.content)


async def test_currencies_are_served_unpaginated_and_complete():
    """`total` counts what was returned because everything is returned: there
    is no page to be a subset of."""

    response = await as_user("/api/v1/currencies")

    assert response.status_code == 200
    payload = body_of(response)
    assert payload["meta"] == {
        "limit": None,
        "total": len(payload["data"]),
        "next_cursor": None,
        "prev_cursor": None,
    }
    by_code = {currency["code"]: currency for currency in payload["data"]}
    assert by_code["USD"] == {
        "code": "USD",
        "symbol": "$",
        "name": "US Dollar",
        "decimals": 2,
    }
    assert list(by_code) == sorted(by_code)


async def test_an_unauthenticated_call_gets_the_error_envelope():
    response = await AsyncClient().get("/api/v1/currencies")

    assert response.status_code == 401
    assert body_of(response)["error"]["code"] == "unauthorized"


async def test_rates_echo_the_target_filter_in_meta(stub_rates):
    stub_rates(StubRateService())

    response = await as_user("/api/v1/currencies/rates/USD?target=RUB")

    assert response.status_code == 200
    payload = body_of(response)
    assert payload["data"] == {"base": "USD", "rates": {"RUB": "82"}}
    assert payload["meta"]["target"] == ["RUB"]
    assert payload["meta"]["fetched_at"] == "2026-08-12T16:51:00+00:00"


async def test_an_unknown_base_is_422_unsupported_currency(stub_rates):
    stub_rates(StubRateService())

    response = await as_user("/api/v1/currencies/rates/XYZ")

    assert response.status_code == 422
    assert body_of(response)["error"]["code"] == "unsupported_currency"


async def test_a_feed_with_nothing_fresh_is_409_rate_unavailable(stub_rates):
    stub_rates(StubRateService(failure=RateUnavailable("stale")))

    response = await as_user("/api/v1/currencies/rates/USD")

    assert response.status_code == 409
    assert body_of(response)["error"]["code"] == "rate_unavailable"


async def test_convert_returns_both_money_objects_and_a_bare_rate(stub_rates):
    stub_rates(StubRateService())

    response = await as_user("/api/v1/currencies/convert?from_code=USD&to_code=RUB&amount=100.00")

    assert response.status_code == 200
    assert body_of(response)["data"] == {
        "from": {"amount": "100.00", "currency": "USD"},
        "to": {"amount": "8200.00", "currency": "RUB"},
        "rate": "82",
    }


async def test_convert_rejects_a_missing_query_param_as_required(stub_rates):
    stub_rates(StubRateService())

    response = await as_user("/api/v1/currencies/convert?from_code=USD")

    assert response.status_code == 422
    error = body_of(response)["error"]
    assert error["code"] == "validation_failed"
    assert {detail["field"] for detail in error["details"]} == {"to_code", "amount"}
    assert {detail["code"] for detail in error["details"]} == {"required"}


async def test_convert_rejects_an_over_precise_amount(stub_rates):
    stub_rates(StubRateService())

    response = await as_user("/api/v1/currencies/convert?from_code=USD&to_code=RUB&amount=100.005")

    assert response.status_code == 422
    assert body_of(response)["error"]["details"][0]["code"] == "amount_precision"

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from data_read_core.query_slices.get_currency_rates.dtos import GetCurrencyRatesQuery
from data_read_core.query_slices.get_currency_rates.http._presenters import (
    present_meta,
    present_rates,
)
from data_read_core.query_slices.get_currency_rates.query_handler import (
    GetCurrencyRatesQueryHandler,
)
from data_read_core.shared.exchange_rates import RateSnapshot, RateUnavailable
from data_read_core.shared.http_contract import UnsupportedCurrency
from data_read_core.shared.money import CURRENCY_CATALOG
from data_read_core.shared.postgres_orm import CurrencyReadModel

pytestmark = pytest.mark.django_db(transaction=True)

FEED_TIME = datetime(2026, 8, 12, 16, 51, tzinfo=UTC)


class StubRateService:
    def __init__(self, snapshot: RateSnapshot | None = None, failure: Exception | None = None):
        self._snapshot = snapshot
        self._failure = failure

    async def snapshot_for(self, base_code: str) -> RateSnapshot:
        if self._failure is not None:
            raise self._failure

        assert self._snapshot is not None
        return self._snapshot


def snapshot() -> RateSnapshot:
    return RateSnapshot(
        base="USD",
        rates={
            "USD": Decimal("1"),
            "EUR": Decimal("0.90"),
            "RUB": Decimal("81.5"),
        },
        fetched_at=FEED_TIME,
    )


def handler(service=None) -> GetCurrencyRatesQueryHandler:
    return GetCurrencyRatesQueryHandler(rate_service=service or StubRateService(snapshot()))


@pytest.fixture(autouse=True)
async def _reference_currencies():
    CURRENCY_CATALOG.reset()
    await CurrencyReadModel.objects.abulk_create(
        [
            CurrencyReadModel(code="USD", name="US Dollar", symbol="$", numeric="840", digits=2),
            CurrencyReadModel(code="EUR", name="Euro", symbol="€", numeric="978", digits=2),
            CurrencyReadModel(
                code="RUB", name="Russian Ruble", symbol="₽", numeric="643", digits=2
            ),
        ],
        ignore_conflicts=True,
    )
    yield
    CURRENCY_CATALOG.reset()


async def test_the_base_comes_from_the_path_and_is_case_insensitive():
    rates = await handler().handle(GetCurrencyRatesQuery(base_code="usd"))

    assert rates.base == "USD"


async def test_an_unknown_base_is_rejected_before_the_feed_is_asked():
    """422, not 409: the code is wrong, and no amount of waiting fixes it."""

    exploding = StubRateService(failure=AssertionError("feed must not be asked"))

    with pytest.raises(UnsupportedCurrency):
        await handler(exploding).handle(GetCurrencyRatesQuery(base_code="XYZ"))


async def test_a_feed_with_no_fresh_reading_surfaces_as_rate_unavailable():
    stalled = StubRateService(failure=RateUnavailable("stale"))

    with pytest.raises(RateUnavailable):
        await handler(stalled).handle(GetCurrencyRatesQuery(base_code="USD"))


async def test_targets_narrow_the_map():
    rates = await handler().handle(
        GetCurrencyRatesQuery(base_code="USD", target_codes=["rub", "EUR"])
    )

    assert set(rates.rates) == {"RUB", "EUR"}


async def test_an_unknown_target_is_rejected_rather_than_dropped_from_the_map():
    """Silently omitting it would look like `rate_unavailable` for a code that
    simply does not exist."""

    with pytest.raises(UnsupportedCurrency):
        await handler().handle(GetCurrencyRatesQuery(base_code="USD", target_codes=["XYZ"]))


async def test_rates_present_as_unpadded_strings():
    rates = await handler().handle(GetCurrencyRatesQuery(base_code="USD"))

    assert present_rates(rates) == {
        "base": "USD",
        "rates": {"EUR": "0.9", "RUB": "81.5", "USD": "1"},
    }


async def test_freshness_and_the_target_filter_ride_in_meta():
    rates = await handler().handle(GetCurrencyRatesQuery(base_code="USD", target_codes=["rub"]))

    assert present_meta(rates) == {
        "fetched_at": "2026-08-12T16:51:00+00:00",
        "target": ["RUB"],
    }


async def test_meta_target_is_null_when_the_whole_map_was_returned():
    rates = await handler().handle(GetCurrencyRatesQuery(base_code="USD"))

    assert present_meta(rates)["target"] is None

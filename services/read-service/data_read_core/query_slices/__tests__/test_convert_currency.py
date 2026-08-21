from datetime import UTC, datetime
from decimal import Decimal

import pytest

from data_read_core.query_slices.convert_currency.dtos import ConvertCurrencyQuery
from data_read_core.query_slices.convert_currency.http._presenters import (
    present_conversion,
    present_meta,
)
from data_read_core.query_slices.convert_currency.query_handler import (
    ConvertCurrencyQueryHandler,
)
from data_read_core.shared.exchange_rates import RateUnavailable
from data_read_core.shared.http_contract import UnsupportedCurrency, ValidationFailed
from data_read_core.shared.money import CURRENCY_CATALOG
from data_read_core.shared.postgres_orm import CurrencyReadModel

pytestmark = pytest.mark.django_db(transaction=True)

FEED_TIME = datetime(2026, 8, 12, 16, 51, tzinfo=UTC)

RATES = {
    ("USD", "RUB"): Decimal("82"),
    ("USD", "JPY"): Decimal("150.256"),
    ("USD", "USD"): Decimal("1"),
    ("JPY", "USD"): Decimal("0.0066"),
}


class StubRateService:
    async def rate_between(self, base_code: str, quote_code: str):
        rate = RATES.get((base_code, quote_code))
        if rate is None:
            raise RateUnavailable(f"no rate {base_code}->{quote_code}")

        return rate, FEED_TIME


def handler() -> ConvertCurrencyQueryHandler:
    return ConvertCurrencyQueryHandler(rate_service=StubRateService())


@pytest.fixture(autouse=True)
async def _reference_currencies():
    CURRENCY_CATALOG.reset()
    await CurrencyReadModel.objects.abulk_create(
        [
            CurrencyReadModel(code="USD", name="US Dollar", symbol="$", numeric="840", digits=2),
            CurrencyReadModel(
                code="RUB", name="Russian Ruble", symbol="₽", numeric="643", digits=2
            ),
            CurrencyReadModel(code="JPY", name="Japanese Yen", symbol="¥", numeric="392", digits=0),
            CurrencyReadModel(code="EUR", name="Euro", symbol="€", numeric="978", digits=2),
        ],
        ignore_conflicts=True,
    )
    yield
    CURRENCY_CATALOG.reset()


async def test_both_sides_are_money_at_their_own_scale():
    conversion = await handler().handle(
        ConvertCurrencyQuery(from_code="USD", to_code="RUB", raw_amount="100.00")
    )

    assert present_conversion(conversion) == {
        "from": {"amount": "100.00", "currency": "USD"},
        "to": {"amount": "8200.00", "currency": "RUB"},
        "rate": "82",
    }


async def test_the_target_scale_governs_the_rounding_not_the_source():
    """JPY has no minor unit, so the result is whole yen even though the source
    amount and the rate both carry fractions."""

    conversion = await handler().handle(
        ConvertCurrencyQuery(from_code="USD", to_code="JPY", raw_amount="10.55")
    )

    assert present_conversion(conversion)["to"] == {"amount": "1585", "currency": "JPY"}


async def test_the_rate_is_not_padded_to_either_currencys_scale():
    conversion = await handler().handle(
        ConvertCurrencyQuery(from_code="USD", to_code="JPY", raw_amount="1")
    )

    assert present_conversion(conversion)["rate"] == "150.256"


async def test_the_amount_is_validated_against_the_source_scale():
    """`?amount=100.005&from_code=USD` is a precision failure, not a rounding
    opportunity."""

    with pytest.raises(ValidationFailed) as failure:
        await handler().handle(
            ConvertCurrencyQuery(from_code="USD", to_code="RUB", raw_amount="100.005")
        )

    assert [detail.code for detail in failure.value.details] == ["amount_precision"]
    assert [detail.field for detail in failure.value.details] == ["amount"]


async def test_a_source_scale_that_allows_no_fractions_rejects_them():
    with pytest.raises(ValidationFailed):
        await handler().handle(
            ConvertCurrencyQuery(from_code="JPY", to_code="USD", raw_amount="10.5")
        )


async def test_an_unknown_code_on_either_side_is_unsupported_currency():
    with pytest.raises(UnsupportedCurrency):
        await handler().handle(
            ConvertCurrencyQuery(from_code="XYZ", to_code="RUB", raw_amount="1.00")
        )

    with pytest.raises(UnsupportedCurrency):
        await handler().handle(
            ConvertCurrencyQuery(from_code="USD", to_code="XYZ", raw_amount="1.00")
        )


async def test_a_supported_pair_the_feed_cannot_quote_is_rate_unavailable():
    with pytest.raises(RateUnavailable):
        await handler().handle(
            ConvertCurrencyQuery(from_code="USD", to_code="EUR", raw_amount="1.00")
        )


async def test_freshness_describes_the_rate_and_rides_in_meta():
    conversion = await handler().handle(
        ConvertCurrencyQuery(from_code="USD", to_code="RUB", raw_amount="1.00")
    )

    assert present_meta(conversion) == {"fetched_at": "2026-08-12T16:51:00+00:00"}


async def test_the_source_amount_is_echoed_at_its_own_scale_not_as_sent():
    conversion = await handler().handle(
        ConvertCurrencyQuery(from_code="USD", to_code="RUB", raw_amount="100")
    )

    assert present_conversion(conversion)["from"] == {"amount": "100.00", "currency": "USD"}

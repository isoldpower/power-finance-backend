from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from ..application import ExchangeRateService, RateUnavailable
from ..application.dtos import RateSnapshotDTO


class CountingProvider:
    name = "counting"

    def __init__(self, rates: dict[str, Decimal], age: timedelta = timedelta(0)) -> None:
        self._rates = rates
        self._age = age
        self.fetches = 0

    async def fetch(self, base_code: str) -> RateSnapshotDTO:
        self.fetches += 1
        return RateSnapshotDTO(
            base=base_code.upper(),
            rates=self._rates,
            fetched_at=datetime.now(UTC) - self._age,
        )


def _service(provider, ttl_seconds=900, max_age_seconds=172800) -> ExchangeRateService:
    return ExchangeRateService(
        provider=provider,
        ttl_seconds=ttl_seconds,
        max_age_seconds=max_age_seconds,
    )


async def test_a_rate_is_the_multiplier_to_the_quote_currency():
    provider = CountingProvider({"USD": Decimal("0.0067")})

    rate, _ = await _service(provider).rate_between("JPY", "USD")

    assert rate == Decimal("0.0067")


async def test_a_second_ask_is_served_from_the_cache():
    provider = CountingProvider({"USD": Decimal("1.1")})
    service = _service(provider)

    await service.rate_between("EUR", "USD")
    await service.rate_between("EUR", "USD")

    assert provider.fetches == 1


async def test_the_same_currency_never_asks_the_feed():
    provider = CountingProvider({})

    rate, _ = await _service(provider).rate_between("USD", "USD")

    assert rate == Decimal(1)
    assert provider.fetches == 0


async def test_a_currency_the_feed_does_not_quote_is_refused():
    provider = CountingProvider({"EUR": Decimal("0.9")})

    with pytest.raises(RateUnavailable):
        await _service(provider).rate_between("USD", "XYZ")


async def test_rates_older_than_the_limit_are_refused_not_served():
    provider = CountingProvider({"USD": Decimal("1.1")}, age=timedelta(days=30))

    with pytest.raises(RateUnavailable):
        await _service(provider, max_age_seconds=3600).rate_between("EUR", "USD")


async def test_an_expired_cache_entry_refetches():
    provider = CountingProvider({"USD": Decimal("1.1")})
    service = _service(provider, ttl_seconds=0)

    await service.rate_between("EUR", "USD")
    await service.rate_between("EUR", "USD")

    assert provider.fetches == 2

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fakes import FakeRedis

from data_read_core.shared.exchange_rates import (
    ExchangeRateService,
    RateProvider,
    RateSnapshot,
    RateUnavailable,
    RedisRateCache,
    get_rates_cache_key,
)

TTL_SECONDS = 900
MAX_AGE_SECONDS = 172800


class RecordingProvider(RateProvider):
    name = "recording"

    def __init__(self, snapshot: RateSnapshot | None = None, failure: Exception | None = None):
        self._snapshot = snapshot
        self._failure = failure
        self.calls: list[str] = []

    async def fetch(self, base_code: str) -> RateSnapshot:
        self.calls.append(base_code)
        if self._failure is not None:
            raise self._failure

        assert self._snapshot is not None
        return self._snapshot


def snapshot(fetched_at: datetime | None = None) -> RateSnapshot:
    return RateSnapshot(
        base="USD",
        rates={"USD": Decimal("1"), "RUB": Decimal("82")},
        fetched_at=fetched_at or datetime.now(UTC),
    )


def build_service(provider: RateProvider, redis: FakeRedis) -> ExchangeRateService:
    return ExchangeRateService(
        provider=provider,
        cache=RedisRateCache(redis, ttl_seconds=TTL_SECONDS),
        max_age_seconds=MAX_AGE_SECONDS,
    )


async def test_a_miss_fetches_and_caches_with_the_configured_ttl(fake_redis: FakeRedis):
    provider = RecordingProvider(snapshot())
    service = build_service(provider, fake_redis)

    served = await service.snapshot_for("usd")

    assert served.base == "USD"
    key, _, ttl = fake_redis.set_calls[0]
    assert key == get_rates_cache_key("USD")
    assert ttl == TTL_SECONDS


async def test_a_hit_does_not_reach_the_provider(fake_redis: FakeRedis):
    provider = RecordingProvider(snapshot())
    service = build_service(provider, fake_redis)

    await service.snapshot_for("USD")
    await service.snapshot_for("USD")

    assert provider.calls == ["USD"]


async def test_a_provider_that_cannot_answer_surfaces_as_rate_unavailable(
    fake_redis: FakeRedis,
):
    service = build_service(
        RecordingProvider(failure=RateUnavailable("feed down")),
        fake_redis,
    )

    with pytest.raises(RateUnavailable):
        await service.snapshot_for("USD")


async def test_a_stalled_feed_is_refused_rather_than_served_silently(fake_redis: FakeRedis):
    """The reading is cached and readable — it is its own timestamp that
    disqualifies it, which a Redis TTL cannot express."""

    stalled = snapshot(datetime.now(UTC) - timedelta(seconds=MAX_AGE_SECONDS + 60))
    service = build_service(RecordingProvider(stalled), fake_redis)

    with pytest.raises(RateUnavailable):
        await service.snapshot_for("USD")


async def test_a_stale_reading_already_in_the_cache_is_refused_too(fake_redis: FakeRedis):
    stalled = snapshot(datetime.now(UTC) - timedelta(seconds=MAX_AGE_SECONDS + 60))
    await fake_redis.set(get_rates_cache_key("USD"), json.dumps(stalled.to_cache()))
    provider = RecordingProvider(snapshot())

    with pytest.raises(RateUnavailable):
        await build_service(provider, fake_redis).snapshot_for("USD")

    assert provider.calls == []


async def test_rate_between_returns_the_multiplier_and_its_timestamp(fake_redis: FakeRedis):
    reading = snapshot()
    service = build_service(RecordingProvider(reading), fake_redis)

    rate, fetched_at = await service.rate_between("USD", "rub")

    assert rate == Decimal("82")
    assert fetched_at == reading.fetched_at


async def test_a_supported_currency_the_feed_omits_is_rate_unavailable(fake_redis: FakeRedis):
    """Our table decides what is SUPPORTED; the feed decides what is QUOTED.
    A gap between the two is a 409, not a 422."""

    service = build_service(RecordingProvider(snapshot()), fake_redis)

    with pytest.raises(RateUnavailable):
        await service.rate_between("USD", "JPY")

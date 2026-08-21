from datetime import timedelta

from .exceptions import RateUnavailable
from .logger_shortcuts import log_snapshot_too_old
from .providers import RateProvider
from .rate_cache import RedisRateCache
from .rate_snapshot import RateSnapshot


class ExchangeRateService:
    """Cache in front of a feed, with an age limit the cache TTL cannot express."""

    def __init__(
        self,
        provider: RateProvider,
        cache: RedisRateCache,
        max_age_seconds: int,
    ) -> None:
        self._provider = provider
        self._cache = cache
        self._max_age = timedelta(seconds=max_age_seconds)
        self._max_age_seconds = max_age_seconds

    async def snapshot_for(self, base_code: str) -> RateSnapshot:
        base = base_code.upper()

        cached = await self._cache.read(base)
        if cached is not None:
            return self._fresh_or_refuse(cached)

        fetched = await self._provider.fetch(base)
        usable = self._fresh_or_refuse(fetched)
        await self._cache.write(usable)

        return usable

    async def rate_between(self, base_code: str, quote_code: str):
        """The multiplier taking one unit of `base_code` to `quote_code`."""

        snapshot = await self.snapshot_for(base_code)
        rate = snapshot.rate_to(quote_code)
        if rate is None:
            raise RateUnavailable(f"No rate from {base_code.upper()} to {quote_code.upper()}")

        return rate, snapshot.fetched_at

    def _fresh_or_refuse(self, snapshot: RateSnapshot) -> RateSnapshot:
        if snapshot.is_fresh(self._max_age):
            return snapshot

        log_snapshot_too_old(
            snapshot.base,
            snapshot.age().total_seconds(),
            self._max_age_seconds,
        )
        raise RateUnavailable(f"Rates for {snapshot.base} are past their freshness limit")

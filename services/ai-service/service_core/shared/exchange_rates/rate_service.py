import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from .contracts import RateProvider
from .exceptions import RateUnavailable
from .logger_shortcuts import log_rates_fetched, log_snapshot_too_old
from .rate_snapshot import RateSnapshot


class ExchangeRateService:
    def __init__(
        self,
        provider: RateProvider,
        ttl_seconds: int,
        max_age_seconds: int,
    ) -> None:
        self._provider = provider
        self._ttl = timedelta(seconds=ttl_seconds)
        self._max_age = timedelta(seconds=max_age_seconds)
        self._max_age_seconds = max_age_seconds
        self._cached: dict[str, RateSnapshot] = {}
        self._lock = asyncio.Lock()

    async def snapshot_for(self, base_code: str) -> RateSnapshot:
        base_upper = base_code.upper()

        cached = self._cached.get(base_upper)
        if cached is not None and cached.is_fresh(self._ttl):
            return self._fresh_or_refuse(cached)

        async with self._lock:
            cached = self._cached.get(base_upper)
            if cached is not None and cached.is_fresh(self._ttl):
                return self._fresh_or_refuse(cached)

            fetched = await self._provider.fetch(base_upper)
            usable = self._fresh_or_refuse(fetched)
            self._cached[base_upper] = usable
            log_rates_fetched(base_upper, len(usable.rates))

            return usable

    async def rate_between(self, base_code: str, quote_code: str) -> tuple[Decimal, RateSnapshot]:
        if base_code.upper() == quote_code.upper():
            return Decimal(1), RateSnapshot(
                base=base_code.upper(),
                rates={},
                fetched_at=datetime.now(UTC),
            )

        snapshot = await self.snapshot_for(base_code)
        rate = snapshot.rate_to(quote_code)
        if rate is None:
            raise RateUnavailable(
                f"no rate from {base_code.upper()} to {quote_code.upper()}",
            )

        return rate, snapshot

    def _fresh_or_refuse(self, snapshot: RateSnapshot) -> RateSnapshot:
        if snapshot.is_fresh(self._max_age):
            return snapshot

        log_snapshot_too_old(
            snapshot.base,
            snapshot.age().total_seconds(),
            self._max_age_seconds,
        )
        raise RateUnavailable(f"rates for {snapshot.base} are older than this service will book")

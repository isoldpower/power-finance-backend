import json

from redis.asyncio import Redis

from .logger_shortcuts import log_served_from_cache
from .rate_snapshot import RateSnapshot


def get_rates_cache_key(base_code: str) -> str:
    return f"read:rates:{base_code.upper()}"


class RedisRateCache:
    """The feed is shared by every user, so the cache is not user-scoped."""

    def __init__(self, redis_client: Redis, ttl_seconds: int) -> None:
        self._redis_client = redis_client
        self._ttl_seconds = ttl_seconds

    async def read(self, base_code: str) -> RateSnapshot | None:
        cached_value = await self._redis_client.get(get_rates_cache_key(base_code))
        if cached_value is None:
            return None

        log_served_from_cache(base_code)
        return RateSnapshot.from_cache(json.loads(cached_value))

    async def write(self, snapshot: RateSnapshot) -> None:
        await self._redis_client.set(
            get_rates_cache_key(snapshot.base),
            json.dumps(snapshot.to_cache()),
            ex=self._ttl_seconds,
        )

from redis.exceptions import RedisError

from data_read_core.shared.redis_cache import get_redis

from .health_probe import HealthProbe

REDIS_CONNECTIVITY_ERRORS: tuple[type[BaseException], ...] = (RedisError, OSError)


class RedisHealthProbe(HealthProbe):
    """`HealthProbe` backed by a Redis PING."""

    @property
    def name(self) -> str:
        return "redis"

    async def is_healthy(self) -> bool:
        try:
            return bool(await get_redis().ping())
        except REDIS_CONNECTIVITY_ERRORS:
            return False

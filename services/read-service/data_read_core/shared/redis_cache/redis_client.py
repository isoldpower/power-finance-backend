from functools import lru_cache

import redis.asyncio as redis
from django.conf import settings


@lru_cache(maxsize=1)
def get_redis() -> redis.Redis:
    """Return the process-wide async Redis client."""
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

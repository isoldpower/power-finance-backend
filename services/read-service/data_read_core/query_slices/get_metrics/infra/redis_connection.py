from redis.asyncio import Redis

from data_read_core.shared.redis_cache import get_redis

from ..config import CacheSchema


def get_metrics_cache_key(
    user_id: int,
    version: str,
    currency: str,
    since: str,
    points: int,
    sections: str,
) -> str:
    return (
        f"read:metrics:{CacheSchema.VERSION}:{user_id}"
        f":v{version}:c{currency}:s{since}:p{points}:x{sections}"
    )


def get_redis_client() -> Redis:
    return get_redis()

from redis.asyncio import Redis

from data_read_core.shared.redis_cache import get_redis

from ..config import CacheSchema


def get_single_cache_key(account_id: str) -> str:
    return f"read:account:{CacheSchema.VERSION}:{account_id}"


def get_redis_client() -> Redis:
    return get_redis()

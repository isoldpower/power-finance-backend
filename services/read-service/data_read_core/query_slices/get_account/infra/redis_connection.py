from redis.asyncio import Redis

from data_read_core.shared.redis_cache import get_redis

CACHE_TTL_SECONDS = 300
ACCOUNT_CACHE_SCHEMA = "s1"


def get_single_cache_key(account_id: str) -> str:
    return f"read:account:{ACCOUNT_CACHE_SCHEMA}:{account_id}"


def get_redis_client() -> Redis:
    return get_redis()

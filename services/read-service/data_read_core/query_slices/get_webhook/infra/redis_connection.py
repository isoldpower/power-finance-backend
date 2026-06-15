from redis.asyncio import Redis

from data_read_core.shared.redis_cache import get_redis

CACHE_TTL_SECONDS = 300


def get_single_cache_key(webhook_id: str) -> str:
    return f"read:webhook:{webhook_id}"


def get_redis_client() -> Redis:
    return get_redis()

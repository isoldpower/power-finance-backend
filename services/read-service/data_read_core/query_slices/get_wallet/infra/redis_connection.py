from redis.asyncio import Redis

from data_read_core.shared.redis_cache import get_redis

from ..config import CacheSchema


def get_single_cache_key(wallet_id: str) -> str:
    return f"read:wallet:{CacheSchema.VERSION}:{wallet_id}"


def get_redis_client() -> Redis:
    return get_redis()

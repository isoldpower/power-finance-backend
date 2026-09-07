from redis.asyncio import Redis

from data_read_core.shared.redis_cache import get_redis

from ..config import CacheSchema


def get_single_cache_key(goal_id: str) -> str:
    return f"read:goal:{CacheSchema.VERSION}:{goal_id}"


def get_redis_client() -> Redis:
    return get_redis()

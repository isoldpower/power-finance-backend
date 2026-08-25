from redis.asyncio import Redis

from data_read_core.shared.redis_cache import get_redis

CACHE_TTL_SECONDS = 300
GOAL_CACHE_SCHEMA = "s1"


def get_single_cache_key(goal_id: str) -> str:
    return f"read:goal:{GOAL_CACHE_SCHEMA}:{goal_id}"


def get_redis_client() -> Redis:
    return get_redis()

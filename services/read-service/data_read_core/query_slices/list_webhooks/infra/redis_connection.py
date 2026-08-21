from redis.asyncio import Redis

from data_read_core.shared.redis_cache import get_redis

CACHE_TTL_SECONDS = 300


def get_list_cache_key(
    user_id: int,
    version: int,
    limit: int,
    cursor: str,
) -> str:
    return f"read:webhooks:{user_id}:v{version}:l{limit}:c{cursor}"


def get_list_version_key(user_id: int) -> str:
    return f"ver:webhooks:{user_id}"


def get_redis_client() -> Redis:
    return get_redis()

from redis.asyncio import Redis

from data_read_core.shared.redis_cache import get_redis

from ..config import CacheSchema


def get_list_cache_key(
    user_id: int,
    version: int,
    kind: str | None,
    limit: int,
    cursor: str,
) -> str:
    return (
        f"read:categories:{CacheSchema.VERSION}:{user_id}"
        f":v{version}:k{kind or 'all'}:l{limit}:c{cursor}"
    )


def get_list_version_key(user_id: int) -> str:
    return f"ver:categories:{user_id}"


def get_redis_client() -> Redis:
    return get_redis()

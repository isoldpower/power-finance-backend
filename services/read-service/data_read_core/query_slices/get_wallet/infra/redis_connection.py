from redis.asyncio import Redis

from data_read_core.shared.redis_cache import get_redis

CACHE_TTL_SECONDS = 300
WALLET_CACHE_SCHEMA = "s2"


def get_single_cache_key(wallet_id: str) -> str:
    return f"read:wallet:{WALLET_CACHE_SCHEMA}:{wallet_id}"


def get_redis_client() -> Redis:
    return get_redis()

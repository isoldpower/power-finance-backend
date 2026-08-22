import hashlib
import json

from redis.asyncio import Redis

from data_read_core.shared.redis_cache import get_redis

CACHE_TTL_SECONDS = 300
WALLET_CACHE_SCHEMA = "s2"


def get_filter_hash(filters: dict) -> str:
    """Stable short digest of the filter set. Canonicalized
    so equivalent filters in any order map to one cache key."""

    canonical = json.dumps(filters, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(canonical.encode()).hexdigest()[:16]


def get_list_cache_key(
    user_id: int,
    version: int,
    filter_hash: str,
    limit: int,
    cursor: str,
) -> str:
    return (
        f"read:wallets:{WALLET_CACHE_SCHEMA}:{user_id}"
        f":v{version}:f{filter_hash}:l{limit}:c{cursor}"
    )


def get_list_version_key(user_id: int) -> str:
    return f"ver:wallets:{user_id}"


def get_redis_client() -> Redis:
    return get_redis()

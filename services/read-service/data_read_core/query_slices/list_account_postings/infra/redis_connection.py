import hashlib
import json

from redis.asyncio import Redis

from data_read_core.shared.redis_cache import get_redis

CACHE_TTL_SECONDS = 300
POSTINGS_CACHE_SCHEMA = "s1"


def get_filter_hash(filters: dict) -> str:
    canonical = json.dumps(filters, sort_keys=True, separators=(",", ":"))

    return hashlib.sha1(canonical.encode()).hexdigest()[:16]


def get_list_cache_key(
    account_id: str,
    version: int,
    filter_hash: str,
    limit: int,
    cursor: str,
) -> str:
    return (
        f"read:account_postings:{POSTINGS_CACHE_SCHEMA}:{account_id}"
        f":v{version}:f{filter_hash}:l{limit}:c{cursor}"
    )


def get_list_version_key(account_id: str) -> str:
    return f"ver:account_postings:{account_id}"


def get_redis_client() -> Redis:
    return get_redis()

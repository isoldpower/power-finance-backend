"""The process-wide async Redis client is a cached singleton."""

from data_read_core.shared.redis_cache import get_redis


def test_get_redis_returns_cached_singleton():
    # lru_cache(maxsize=1): every caller shares one connection pool. Construction
    # is lazy (from_url opens no socket), so this is safe without a live Redis.
    assert get_redis() is get_redis()

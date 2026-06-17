"""The process-wide async Redis client is a cached singleton."""

from data_read_core.shared.redis_cache import get_redis


def test_get_redis_returns_cached_singleton():
    assert get_redis() is get_redis()

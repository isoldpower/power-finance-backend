from functools import lru_cache

from django.conf import settings

from data_read_core.shared.redis_cache import get_redis

from .providers import OpenExchangeRatesProvider, RateProvider, StaticRateProvider
from .rate_cache import RedisRateCache
from .rate_service import ExchangeRateService


def build_provider() -> RateProvider:
    configured = settings.EXCHANGE_RATES["PROVIDER"]
    if configured == "static":
        return StaticRateProvider()

    return OpenExchangeRatesProvider(
        base_url=settings.EXCHANGE_RATES["BASE_URL"],
        timeout_seconds=settings.EXCHANGE_RATES["TIMEOUT_SECONDS"],
    )


@lru_cache(maxsize=1)
def get_rate_service() -> ExchangeRateService:
    """Process-wide, like the Redis client it holds."""

    return ExchangeRateService(
        provider=build_provider(),
        cache=RedisRateCache(
            redis_client=get_redis(),
            ttl_seconds=settings.EXCHANGE_RATES["TTL_SECONDS"],
        ),
        max_age_seconds=settings.EXCHANGE_RATES["MAX_AGE_SECONDS"],
    )

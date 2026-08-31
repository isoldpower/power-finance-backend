from functools import lru_cache

from .config import get_exchange_rate_settings
from .contracts import RateProvider
from .open_exchange_provider import OpenExchangeRatesProvider
from .rate_service import ExchangeRateService


def build_provider() -> RateProvider:
    settings = get_exchange_rate_settings()

    return OpenExchangeRatesProvider(
        base_url=settings.base_url,
        timeout_seconds=settings.timeout_seconds,
    )


@lru_cache(maxsize=1)
def get_rate_service() -> ExchangeRateService:
    settings = get_exchange_rate_settings()

    return ExchangeRateService(
        provider=build_provider(),
        ttl_seconds=settings.ttl_seconds,
        max_age_seconds=settings.max_age_seconds,
    )

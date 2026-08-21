"""Exchange rates: a feed behind an interface, cached, with staleness treated as
a failure rather than a silently old number."""

from .exceptions import RateUnavailable
from .factory import build_provider, get_rate_service
from .providers import OpenExchangeRatesProvider, RateProvider, StaticRateProvider
from .rate_cache import RedisRateCache, get_rates_cache_key
from .rate_rendering import MAX_RATE_FRACTION_DIGITS, format_rate
from .rate_service import ExchangeRateService
from .rate_snapshot import RateSnapshot

__all__ = [
    "MAX_RATE_FRACTION_DIGITS",
    "ExchangeRateService",
    "OpenExchangeRatesProvider",
    "RateProvider",
    "RateSnapshot",
    "RateUnavailable",
    "RedisRateCache",
    "StaticRateProvider",
    "build_provider",
    "format_rate",
    "get_rate_service",
    "get_rates_cache_key",
]

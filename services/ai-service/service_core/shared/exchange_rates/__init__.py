"""Exchange rates: the feed read-service books against, behind a cache, with
staleness treated as a failure rather than a silently old number."""

from .config import ExchangeRateSettings, get_exchange_rate_settings
from .contracts import RateProvider
from .exceptions import RateUnavailable
from .factory import build_provider, get_rate_service
from .open_exchange_provider import OpenExchangeRatesProvider
from .rate_service import ExchangeRateService
from .rate_snapshot import RateSnapshot

__all__ = [
    "ExchangeRateService",
    "ExchangeRateSettings",
    "OpenExchangeRatesProvider",
    "RateProvider",
    "RateSnapshot",
    "RateUnavailable",
    "build_provider",
    "get_exchange_rate_settings",
    "get_rate_service",
]

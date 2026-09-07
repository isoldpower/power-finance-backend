from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[4] / ".env"


class ExchangeRateSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    provider: str = Field(alias="EXCHANGE_RATES_PROVIDER")
    base_url: str = Field(alias="EXCHANGE_RATES_BASE_URL")
    timeout_seconds: float = Field(alias="EXCHANGE_RATES_TIMEOUT_SECONDS")
    ttl_seconds: int = Field(alias="EXCHANGE_RATES_TTL_SECONDS")
    max_age_seconds: int = Field(alias="EXCHANGE_RATES_MAX_AGE_SECONDS")


@lru_cache(maxsize=1)
def get_exchange_rate_settings() -> ExchangeRateSettings:
    return ExchangeRateSettings()


class FeedPayloadKey(StrEnum):
    RESULT = "result"
    RATES = "rates"
    UPDATED_AT = "time_last_update_unix"
    ERROR_TYPE = "error-type"


class FeedResult(StrEnum):
    SUCCESS = "success"

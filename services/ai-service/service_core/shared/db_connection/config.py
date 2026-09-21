from enum import StrEnum
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    database_url: str = Field(alias="AI_DATABASE_URL")


@lru_cache(maxsize=1)
def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings()


class AccountGroup(StrEnum):
    ASSETS = "assets"
    LIABILITIES = "liabilities"
    EQUITY = "equity"

    @classmethod
    def debit_normal(cls) -> tuple["AccountGroup", ...]:
        return (cls.ASSETS,)

    @classmethod
    def credit_normal(cls) -> tuple["AccountGroup", ...]:
        return (cls.LIABILITIES, cls.EQUITY)

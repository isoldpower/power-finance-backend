from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    kafka_bootstrap_servers: str = Field(alias="KAFKA_BOOTSTRAP_SERVERS")
    kafka_outbox_topic: str = Field(alias="KAFKA_OUTBOX_TOPIC")
    kafka_group_id: str = Field(alias="KAFKA_AI_GROUP_ID")
    kafka_retry_topic: str = Field(alias="KAFKA_RETRY_TOPIC")
    kafka_dlq_topic: str = Field(alias="KAFKA_DLQ_TOPIC")

    log_level: str = Field(alias="LOG_LEVEL")


@lru_cache(maxsize=1)
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()

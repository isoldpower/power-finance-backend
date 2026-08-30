"""This service's health probes, plus the shared guard they plug into.

The guard and the `HealthProbe` contract live in `kafka_consumer_py`; what is
local is which stores this service actually blocks consumption on.
"""

from kafka_consumer_py.health import HealthGuardedHandler, HealthProbe

from .elasticsearch_health_probe import (
    ELASTICSEARCH_CONNECTIVITY_ERRORS,
    ElasticsearchHealthProbe,
)
from .postgres_health_probe import POSTGRES_CONNECTIVITY_ERRORS, PostgresHealthProbe
from .redis_health_probe import REDIS_CONNECTIVITY_ERRORS, RedisHealthProbe

__all__ = [
    "ELASTICSEARCH_CONNECTIVITY_ERRORS",
    "POSTGRES_CONNECTIVITY_ERRORS",
    "REDIS_CONNECTIVITY_ERRORS",
    "ElasticsearchHealthProbe",
    "HealthGuardedHandler",
    "HealthProbe",
    "PostgresHealthProbe",
    "RedisHealthProbe",
]

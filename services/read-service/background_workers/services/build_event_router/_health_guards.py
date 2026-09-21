from data_read_core.shared.health_guard import (
    ELASTICSEARCH_CONNECTIVITY_ERRORS,
    POSTGRES_CONNECTIVITY_ERRORS,
    REDIS_CONNECTIVITY_ERRORS,
    HealthGuardedHandler,
)
from kafka_consumer_py import (
    ExecutionPlan,
    Handler,
)

from ._types import ProbesDictionary


def guard_all(plan: ExecutionPlan, probes: ProbesDictionary) -> Handler:
    guarded: Handler = HealthGuardedHandler(
        plan,
        probes.postgres_probe,
        guarded_errors=POSTGRES_CONNECTIVITY_ERRORS,
    )
    guarded = HealthGuardedHandler(
        guarded,
        probes.redis_probe,
        guarded_errors=REDIS_CONNECTIVITY_ERRORS,
    )
    guarded = HealthGuardedHandler(
        guarded,
        probes.elasticsearch_probe,
        guarded_errors=ELASTICSEARCH_CONNECTIVITY_ERRORS,
    )

    return guarded

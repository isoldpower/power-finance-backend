from kafka_consumer_py import ExecutionPlan, Handler, HealthGuardedHandler
from service_core.shared.health_guard import POSTGRES_CONNECTIVITY_ERRORS

from ._types import ProbesDictionary


def guard_all(plan: ExecutionPlan, probes: ProbesDictionary) -> Handler:
    guarded: Handler = HealthGuardedHandler(
        plan,
        probes.postgres_probe,
        guarded_errors=POSTGRES_CONNECTIVITY_ERRORS,
    )

    return guarded

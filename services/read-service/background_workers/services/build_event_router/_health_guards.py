from data_read_core.shared.health_guard import (
    ELASTICSEARCH_CONNECTIVITY_ERRORS,
    POSTGRES_CONNECTIVITY_ERRORS,
    REDIS_CONNECTIVITY_ERRORS,
    HealthGuardedHandler,
)
from data_read_core.write_reactions import AdvanceEsAppliedSeq, TrackEsPendingSeq
from google.protobuf.message import Message
from kafka_consumer_py import (
    ExecutionPlan,
    Handler,
    SyncProcessGroup,
)

from ._types import ProbesDictionary


def guard_postgres_lane(plan: ExecutionPlan, probes: ProbesDictionary) -> Handler:
    guarded: Handler = HealthGuardedHandler(
        plan,
        probes.postgres_probe,
        guarded_errors=POSTGRES_CONNECTIVITY_ERRORS,
    )

    return HealthGuardedHandler(
        guarded,
        probes.redis_probe,
        guarded_errors=REDIS_CONNECTIVITY_ERRORS,
    )


def guard_search_lane(
    plan: ExecutionPlan,
    probes: ProbesDictionary,
    payload_type: type[Message],
) -> Handler:
    guarded: Handler = HealthGuardedHandler(
        TrackEsPendingSeq(plan, payload_type),
        probes.postgres_probe,
        guarded_errors=POSTGRES_CONNECTIVITY_ERRORS,
    )

    return HealthGuardedHandler(
        guarded,
        probes.elasticsearch_probe,
        guarded_errors=ELASTICSEARCH_CONNECTIVITY_ERRORS,
    )


def guard_search_watermark_lane(
    payload_type: type[Message],
    probes: ProbesDictionary,
) -> Handler:
    watermark_plan = ExecutionPlan([SyncProcessGroup([AdvanceEsAppliedSeq(payload_type)])])

    return guard_search_lane(watermark_plan, probes, payload_type)

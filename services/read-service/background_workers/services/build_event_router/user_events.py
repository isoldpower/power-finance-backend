from data_read_core.shared.health_guard import (
    POSTGRES_CONNECTIVITY_ERRORS,
    HealthGuardedHandler,
)
from data_read_core.shared.kafka_updates import (
    EventRouter,
    ExecutionPlan,
    SyncProcessGroup,
)
from data_read_core.write_reactions import ProjectUserReadModel

from ._types import ProbesDictionary


def subscribe_user_synced(
    router: EventRouter,
    probes: ProbesDictionary,
):
    user_synced = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    ProjectUserReadModel(),
                ]
            ),
        ]
    )
    guarded_handler = HealthGuardedHandler(
        user_synced,
        probes.postgres_probe,
        guarded_errors=POSTGRES_CONNECTIVITY_ERRORS,
    )

    router.register("UserSynced", guarded_handler)

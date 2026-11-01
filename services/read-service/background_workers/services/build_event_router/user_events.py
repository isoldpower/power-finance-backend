from data_read_core.shared.health_guard import (
    POSTGRES_CONNECTIVITY_ERRORS,
    HealthGuardedHandler,
)
from data_read_core.write_reactions import ProjectUserReadModel
from kafka_consumer_py import (
    ExecutionPlan,
    SyncProcessGroup,
)

from ._types import ProbesDictionary, ProjectionRouters


def subscribe_user_synced(
    routers: ProjectionRouters,
    probes: ProbesDictionary,
):
    user_synced = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    ProjectUserReadModel(),
                ],
                atomic=True,
            ),
        ]
    )
    guarded_handler = HealthGuardedHandler(
        user_synced,
        probes.postgres_probe,
        guarded_errors=POSTGRES_CONNECTIVITY_ERRORS,
    )

    routers.postgres.register("UserSynced", guarded_handler)

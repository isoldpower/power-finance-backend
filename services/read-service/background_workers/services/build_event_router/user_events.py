from data_read_core.shared.health_guard import (
    POSTGRES_CONNECTIVITY_ERRORS,
    HealthGuardedHandler,
    HealthProbe,
)
from data_read_core.shared.kafka_updates import (
    EventRouter,
    ExecutionPlan,
    SyncProcessGroup,
)
from data_read_core.write_reactions import ProjectUserReadModel


def subscribe_user_synced(
    router: EventRouter,
    postgres_probe: HealthProbe,
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
        postgres_probe,
        guarded_errors=POSTGRES_CONNECTIVITY_ERRORS,
    )

    router.register("UserSynced", guarded_handler)

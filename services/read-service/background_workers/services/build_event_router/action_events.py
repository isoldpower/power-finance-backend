from data_read_core.write_reactions import (
    BumpActionListVersion,
    RaiseActionReadModel,
    ResolveActionReadModel,
    TrackAppliedSeq,
)
from kafka_consumer_py import (
    ExecutionPlan,
    SyncProcessGroup,
)
from kafka_messages import (
    ActionRaised,
    ActionResolved,
)

from ._health_guards import guard_postgres_lane
from ._types import ProbesDictionary, ProjectionRouters


def subscribe_action_raised(routers: ProjectionRouters, probes: ProbesDictionary):
    action_raised = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(RaiseActionReadModel(), ActionRaised),
                    BumpActionListVersion(ActionRaised),
                ],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register(
        "ActionRaised",
        guard_postgres_lane(action_raised, probes),
    )


def subscribe_action_resolved(routers: ProjectionRouters, probes: ProbesDictionary):
    action_resolved = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(ResolveActionReadModel(), ActionResolved),
                    BumpActionListVersion(ActionResolved),
                ],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register(
        "ActionResolved",
        guard_postgres_lane(action_resolved, probes),
    )

from data_read_core.write_reactions import (
    BumpActionListVersion,
    RaiseActionReadModel,
    ResolveActionReadModel,
)
from kafka_consumer_py import (
    EventRouter,
    ExecutionPlan,
    SyncProcessGroup,
)
from kafka_messages import (
    ActionRaised,
    ActionResolved,
)

from ._health_guards import guard_all
from ._types import ProbesDictionary


def subscribe_action_raised(router: EventRouter, probes: ProbesDictionary):
    action_raised = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    RaiseActionReadModel(),
                    BumpActionListVersion(ActionRaised),
                ]
            ),
        ]
    )

    router.register(
        "ActionRaised",
        guard_all(action_raised, probes),
    )


def subscribe_action_resolved(router: EventRouter, probes: ProbesDictionary):
    action_resolved = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    ResolveActionReadModel(),
                    BumpActionListVersion(ActionResolved),
                ]
            ),
        ]
    )

    router.register(
        "ActionResolved",
        guard_all(action_resolved, probes),
    )

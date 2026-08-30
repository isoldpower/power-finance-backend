from data_read_core.write_reactions import (
    BumpGoalListVersion,
    BumpTransactionListVersion,
    CreateGoalReadModel,
    EvictGoalCache,
    RemoveGoalReadModel,
    RenameGoalInTransactions,
    TrackAppliedSeq,
    UpdateGoalReadModel,
)
from kafka_consumer_py import (
    EventRouter,
    ExecutionPlan,
    SyncProcessGroup,
)
from kafka_messages import (
    GoalCreated,
    GoalDeleted,
    GoalUpdated,
)

from ._health_guards import guard_all
from ._types import ProbesDictionary


def subscribe_goal_created(
    router: EventRouter,
    probes: ProbesDictionary,
):
    goal_created = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(CreateGoalReadModel(), GoalCreated),
                    BumpGoalListVersion(GoalCreated),
                ]
            ),
        ]
    )

    router.register(
        "GoalCreated",
        guard_all(goal_created, probes),
    )


def subscribe_goal_updated(
    router: EventRouter,
    probes: ProbesDictionary,
):
    goal_updated = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(UpdateGoalReadModel(), GoalUpdated),
                    RenameGoalInTransactions(),
                    EvictGoalCache(GoalUpdated),
                    BumpGoalListVersion(GoalUpdated),
                    BumpTransactionListVersion(GoalUpdated),
                ]
            ),
        ]
    )

    router.register(
        "GoalUpdated",
        guard_all(goal_updated, probes),
    )


def subscribe_goal_deleted(
    router: EventRouter,
    probes: ProbesDictionary,
):
    goal_deleted = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(RemoveGoalReadModel(), GoalDeleted),
                    EvictGoalCache(),
                    BumpGoalListVersion(GoalDeleted),
                ]
            ),
        ]
    )

    router.register(
        "GoalDeleted",
        guard_all(goal_deleted, probes),
    )

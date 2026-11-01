from data_read_core.write_reactions import (
    BumpGoalListVersion,
    BumpTransactionListVersion,
    CreateGoalReadModel,
    EvictGoalCache,
    IndexGoalDocument,
    RemoveGoalDocument,
    RemoveGoalReadModel,
    RenameGoalInTransactions,
    TrackAppliedSeq,
    TrackEsAppliedSeq,
    UpdateGoalDocument,
    UpdateGoalReadModel,
)
from kafka_consumer_py import (
    ExecutionPlan,
    SyncProcessGroup,
)
from kafka_messages import (
    GoalCreated,
    GoalDeleted,
    GoalUpdated,
)

from ._health_guards import guard_postgres_lane, guard_search_lane
from ._types import ProbesDictionary, ProjectionRouters


def subscribe_goal_created(
    routers: ProjectionRouters,
    probes: ProbesDictionary,
):
    postgres_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(CreateGoalReadModel(), GoalCreated),
                    BumpGoalListVersion(GoalCreated),
                ],
                atomic=True,
            ),
        ]
    )
    search_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [TrackEsAppliedSeq(IndexGoalDocument(), GoalCreated)],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register("GoalCreated", guard_postgres_lane(postgres_plan, probes))
    routers.search.register("GoalCreated", guard_search_lane(search_plan, probes))


def subscribe_goal_updated(
    routers: ProjectionRouters,
    probes: ProbesDictionary,
):
    postgres_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(UpdateGoalReadModel(), GoalUpdated),
                    RenameGoalInTransactions(),
                    EvictGoalCache(GoalUpdated),
                    BumpGoalListVersion(GoalUpdated),
                    BumpTransactionListVersion(GoalUpdated),
                ],
                atomic=True,
            ),
        ]
    )
    search_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [TrackEsAppliedSeq(UpdateGoalDocument(), GoalUpdated)],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register("GoalUpdated", guard_postgres_lane(postgres_plan, probes))
    routers.search.register("GoalUpdated", guard_search_lane(search_plan, probes))


def subscribe_goal_deleted(
    routers: ProjectionRouters,
    probes: ProbesDictionary,
):
    postgres_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(RemoveGoalReadModel(), GoalDeleted),
                    EvictGoalCache(),
                    BumpGoalListVersion(GoalDeleted),
                ],
                atomic=True,
            ),
        ]
    )
    search_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [TrackEsAppliedSeq(RemoveGoalDocument(), GoalDeleted)],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register("GoalDeleted", guard_postgres_lane(postgres_plan, probes))
    routers.search.register("GoalDeleted", guard_search_lane(search_plan, probes))

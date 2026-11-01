from data_read_core.write_reactions import (
    BumpAutomationListVersion,
    IndexAutomationDocument,
    ProjectAutomationReadModel,
    RecordAutomationRun,
    RecordAutomationRunDocument,
    RemoveAutomationDocument,
    RemoveAutomationReadModel,
    TrackAppliedSeq,
    TrackEsAppliedSeq,
)
from kafka_consumer_py import ExecutionPlan, SyncProcessGroup
from kafka_messages import (
    AutomationCreated,
    AutomationDeleted,
    AutomationRan,
    AutomationUpdated,
)

from ._health_guards import guard_postgres_lane, guard_search_lane
from ._types import ProbesDictionary, ProjectionRouters


def subscribe_automation_created(routers: ProjectionRouters, probes: ProbesDictionary):
    postgres_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(
                        ProjectAutomationReadModel(AutomationCreated),
                        AutomationCreated,
                    ),
                    BumpAutomationListVersion(AutomationCreated),
                ],
                atomic=True,
            ),
        ]
    )
    search_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackEsAppliedSeq(
                        IndexAutomationDocument(AutomationCreated),
                        AutomationCreated,
                    )
                ],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register("AutomationCreated", guard_postgres_lane(postgres_plan, probes))
    routers.search.register(
        "AutomationCreated", guard_search_lane(search_plan, probes, AutomationCreated)
    )


def subscribe_automation_updated(routers: ProjectionRouters, probes: ProbesDictionary):
    postgres_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(
                        ProjectAutomationReadModel(AutomationUpdated),
                        AutomationUpdated,
                    ),
                    BumpAutomationListVersion(AutomationUpdated),
                ],
                atomic=True,
            ),
        ]
    )
    search_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackEsAppliedSeq(
                        IndexAutomationDocument(AutomationUpdated),
                        AutomationUpdated,
                    )
                ],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register("AutomationUpdated", guard_postgres_lane(postgres_plan, probes))
    routers.search.register(
        "AutomationUpdated", guard_search_lane(search_plan, probes, AutomationUpdated)
    )


def subscribe_automation_deleted(routers: ProjectionRouters, probes: ProbesDictionary):
    postgres_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(RemoveAutomationReadModel(), AutomationDeleted),
                    BumpAutomationListVersion(AutomationDeleted),
                ],
                atomic=True,
            ),
        ]
    )
    search_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [TrackEsAppliedSeq(RemoveAutomationDocument(), AutomationDeleted)],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register("AutomationDeleted", guard_postgres_lane(postgres_plan, probes))
    routers.search.register(
        "AutomationDeleted", guard_search_lane(search_plan, probes, AutomationDeleted)
    )


def subscribe_automation_ran(routers: ProjectionRouters, probes: ProbesDictionary):
    postgres_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(RecordAutomationRun(), AutomationRan),
                    BumpAutomationListVersion(AutomationRan),
                ],
                atomic=True,
            ),
        ]
    )
    search_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [TrackEsAppliedSeq(RecordAutomationRunDocument(), AutomationRan)],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register("AutomationRan", guard_postgres_lane(postgres_plan, probes))
    routers.search.register("AutomationRan", guard_search_lane(search_plan, probes, AutomationRan))

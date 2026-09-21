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
from kafka_consumer_py import EventRouter, ExecutionPlan, SyncProcessGroup
from kafka_messages import (
    AutomationCreated,
    AutomationDeleted,
    AutomationRan,
    AutomationUpdated,
)

from ._health_guards import guard_all
from ._types import ProbesDictionary


def subscribe_automation_created(router: EventRouter, probes: ProbesDictionary):
    plan = ExecutionPlan(
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

    router.register("AutomationCreated", guard_all(plan, probes))


def subscribe_automation_updated(router: EventRouter, probes: ProbesDictionary):
    plan = ExecutionPlan(
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

    router.register("AutomationUpdated", guard_all(plan, probes))


def subscribe_automation_deleted(router: EventRouter, probes: ProbesDictionary):
    plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(RemoveAutomationReadModel(), AutomationDeleted),
                    BumpAutomationListVersion(AutomationDeleted),
                ],
                atomic=True,
            ),
            SyncProcessGroup(
                [TrackEsAppliedSeq(RemoveAutomationDocument(), AutomationDeleted)],
                atomic=True,
            ),
        ]
    )

    router.register("AutomationDeleted", guard_all(plan, probes))


def subscribe_automation_ran(router: EventRouter, probes: ProbesDictionary):
    plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(RecordAutomationRun(), AutomationRan),
                    BumpAutomationListVersion(AutomationRan),
                ],
                atomic=True,
            ),
            SyncProcessGroup(
                [TrackEsAppliedSeq(RecordAutomationRunDocument(), AutomationRan)],
                atomic=True,
            ),
        ]
    )

    router.register("AutomationRan", guard_all(plan, probes))

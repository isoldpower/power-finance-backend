from data_read_core.write_reactions import (
    BumpAutomationListVersion,
    ProjectAutomationReadModel,
    RecordAutomationRun,
    RemoveAutomationReadModel,
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
                    ProjectAutomationReadModel(AutomationCreated),
                    BumpAutomationListVersion(AutomationCreated),
                ]
            ),
        ]
    )

    router.register("AutomationCreated", guard_all(plan, probes))


def subscribe_automation_updated(router: EventRouter, probes: ProbesDictionary):
    plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    ProjectAutomationReadModel(AutomationUpdated),
                    BumpAutomationListVersion(AutomationUpdated),
                ]
            ),
        ]
    )

    router.register("AutomationUpdated", guard_all(plan, probes))


def subscribe_automation_deleted(router: EventRouter, probes: ProbesDictionary):
    plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    RemoveAutomationReadModel(),
                    BumpAutomationListVersion(AutomationDeleted),
                ]
            ),
        ]
    )

    router.register("AutomationDeleted", guard_all(plan, probes))


def subscribe_automation_ran(router: EventRouter, probes: ProbesDictionary):
    plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    RecordAutomationRun(),
                    BumpAutomationListVersion(AutomationRan),
                ]
            ),
        ]
    )

    router.register("AutomationRan", guard_all(plan, probes))

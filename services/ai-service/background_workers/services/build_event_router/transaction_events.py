from kafka_consumer_py import EventRouter, ExecutionPlan, SyncProcessGroup
from service_core.write_reactions import (
    transaction_created,
    transaction_deleted,
    transaction_updated,
)

from ._health_guards import guard_all
from ._template_accounts import build_created_dispatcher, build_updated_dispatcher
from ._types import ProbesDictionary


def subscribe_transaction_created(router: EventRouter, probes: ProbesDictionary) -> None:
    plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    transaction_created.ProjectTransaction(),
                    transaction_created.DispatchPostings(build_created_dispatcher),
                ]
            ),
        ]
    )

    router.register(
        "TransactionCreated",
        guard_all(plan, probes),
    )


def subscribe_transaction_updated(router: EventRouter, probes: ProbesDictionary) -> None:
    plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    transaction_updated.UpdateProjectedTransactionAmount(),
                    transaction_updated.DispatchPostings(build_updated_dispatcher),
                ]
            ),
        ]
    )

    router.register(
        "TransactionUpdated",
        guard_all(plan, probes),
    )


def subscribe_transaction_deleted(router: EventRouter, probes: ProbesDictionary) -> None:
    plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    transaction_deleted.RemovePostings(),
                    transaction_deleted.SoftDeleteProjectedTransaction(),
                ]
            ),
        ]
    )

    router.register(
        "TransactionDeleted",
        guard_all(plan, probes),
    )

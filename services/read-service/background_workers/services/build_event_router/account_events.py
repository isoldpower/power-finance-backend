from data_read_core.write_reactions import (
    BumpAccountListVersion,
    CreateAccountPostingReadModel,
    CreateAccountReadModel,
    EvictAccountCache,
    EvictTransactionCache,
    RecordAccountDispatch,
    RemoveAccountPostingReadModel,
    UpdateAccountReadModel,
)
from kafka_consumer_py import (
    ExecutionPlan,
    SyncProcessGroup,
)
from kafka_messages import (
    AccountCreated,
    AccountPostingCreated,
    AccountPostingDeleted,
    AccountPostingsDispatched,
    AccountUpdated,
)

from ._health_guards import guard_postgres_lane
from ._types import ProbesDictionary, ProjectionRouters


def subscribe_account_created(
    routers: ProjectionRouters,
    probes: ProbesDictionary,
):
    account_created = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    CreateAccountReadModel(),
                    BumpAccountListVersion(AccountCreated),
                ],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register(
        "AccountCreated",
        guard_postgres_lane(account_created, probes),
    )


def subscribe_account_updated(
    routers: ProjectionRouters,
    probes: ProbesDictionary,
):
    account_updated = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    UpdateAccountReadModel(),
                    BumpAccountListVersion(AccountUpdated),
                    EvictAccountCache(AccountUpdated),
                ],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register(
        "AccountUpdated",
        guard_postgres_lane(account_updated, probes),
    )


def subscribe_account_posting_created(
    routers: ProjectionRouters,
    probes: ProbesDictionary,
):
    posting_created = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    CreateAccountPostingReadModel(),
                    EvictTransactionCache(AccountPostingCreated),
                ],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register(
        "AccountPostingCreated",
        guard_postgres_lane(posting_created, probes),
    )


def subscribe_account_posting_deleted(
    routers: ProjectionRouters,
    probes: ProbesDictionary,
):
    posting_deleted = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    RemoveAccountPostingReadModel(),
                    EvictTransactionCache(AccountPostingDeleted),
                ],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register(
        "AccountPostingDeleted",
        guard_postgres_lane(posting_deleted, probes),
    )


def subscribe_account_postings_dispatched(
    routers: ProjectionRouters,
    probes: ProbesDictionary,
):
    postings_dispatched = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    RecordAccountDispatch(),
                    EvictTransactionCache(AccountPostingsDispatched),
                ],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register(
        "AccountPostingsDispatched",
        guard_postgres_lane(postings_dispatched, probes),
    )

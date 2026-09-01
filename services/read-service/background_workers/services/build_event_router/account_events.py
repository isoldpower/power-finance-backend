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
    EventRouter,
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

from ._health_guards import guard_all
from ._types import ProbesDictionary


def subscribe_account_created(
    router: EventRouter,
    probes: ProbesDictionary,
):
    account_created = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    CreateAccountReadModel(),
                    BumpAccountListVersion(AccountCreated),
                ]
            ),
        ]
    )

    router.register(
        "AccountCreated",
        guard_all(account_created, probes),
    )


def subscribe_account_updated(
    router: EventRouter,
    probes: ProbesDictionary,
):
    account_updated = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    UpdateAccountReadModel(),
                    BumpAccountListVersion(AccountUpdated),
                    EvictAccountCache(AccountUpdated),
                ]
            ),
        ]
    )

    router.register(
        "AccountUpdated",
        guard_all(account_updated, probes),
    )


def subscribe_account_posting_created(
    router: EventRouter,
    probes: ProbesDictionary,
):
    posting_created = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    CreateAccountPostingReadModel(),
                    EvictTransactionCache(AccountPostingCreated),
                ]
            ),
        ]
    )

    router.register(
        "AccountPostingCreated",
        guard_all(posting_created, probes),
    )


def subscribe_account_posting_deleted(
    router: EventRouter,
    probes: ProbesDictionary,
):
    posting_deleted = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    RemoveAccountPostingReadModel(),
                    EvictTransactionCache(AccountPostingDeleted),
                ]
            ),
        ]
    )

    router.register(
        "AccountPostingDeleted",
        guard_all(posting_deleted, probes),
    )


def subscribe_account_postings_dispatched(
    router: EventRouter,
    probes: ProbesDictionary,
):
    postings_dispatched = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    RecordAccountDispatch(),
                    EvictTransactionCache(AccountPostingsDispatched),
                ]
            ),
        ]
    )

    router.register(
        "AccountPostingsDispatched",
        guard_all(postings_dispatched, probes),
    )

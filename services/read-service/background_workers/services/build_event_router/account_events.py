"""The ledger events ai-service publishes.

Deliberately not wrapped in `TrackAppliedSeq`: that records one high-water mark
per user of the *write-service* outbox sequence, and ai-service publishes from
its own independent sequence. Feeding those numbers into the same counter would
let an unrelated ledger event advance the mark a client is waiting on and make
read-your-writes report a write as landed before it was. Read-your-writes on
postings is not reachable through that counter anyway — ai-service only reacts
once the client's write has already returned.
"""

from data_read_core.write_reactions import (
    BumpAccountListVersion,
    BumpAccountPostingsVersion,
    CreateAccountPostingReadModel,
    CreateAccountReadModel,
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
                    BumpAccountPostingsVersion(AccountPostingCreated),
                    # The transaction detail carries its postings, so a new leg
                    # makes the cached transaction stale even though the
                    # transaction row itself did not change.
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
                    BumpAccountPostingsVersion(AccountPostingDeleted),
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

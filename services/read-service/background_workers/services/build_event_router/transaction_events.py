from data_read_core.shared.kafka_updates import (
    EventRouter,
    ExecutionPlan,
    SyncProcessGroup,
)
from data_read_core.write_reactions import (
    BumpTransactionListVersion,
    BumpWalletListVersion,
    CreateTransactionReadModel,
    EvictTransactionCache,
    EvictWalletCache,
    IndexTransactionDocument,
    RemoveTransactionDocument,
    RemoveTransactionReadModel,
    TrackAppliedSeq,
    TrackEsAppliedSeq,
    UpdateTransactionDocument,
    UpdateTransactionReadModel,
)
from kafka_messages import TransactionCreated, TransactionDeleted, TransactionUpdated

from ._health_guards import guard_all
from ._types import ProbesDictionary


def subscribe_transaction_created(
    router: EventRouter,
    probes: ProbesDictionary,
):
    transaction_created = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(CreateTransactionReadModel(), TransactionCreated),
                    EvictWalletCache(TransactionCreated),
                    BumpTransactionListVersion(TransactionCreated),
                    BumpWalletListVersion(TransactionCreated),
                ]
            ),
            SyncProcessGroup([TrackEsAppliedSeq(IndexTransactionDocument(), TransactionCreated)]),
        ]
    )

    router.register(
        "TransactionCreated",
        guard_all(transaction_created, probes),
    )


def subscribe_transaction_deleted(
    router: EventRouter,
    probes: ProbesDictionary,
):
    transaction_deleted = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(RemoveTransactionReadModel(), TransactionDeleted),
                    EvictWalletCache(TransactionDeleted),
                    EvictTransactionCache(TransactionDeleted),
                    BumpTransactionListVersion(TransactionDeleted),
                    BumpWalletListVersion(TransactionDeleted),
                ]
            ),
            SyncProcessGroup([TrackEsAppliedSeq(RemoveTransactionDocument(), TransactionDeleted)]),
        ]
    )

    router.register(
        "TransactionDeleted",
        guard_all(transaction_deleted, probes),
    )


def subscribe_transaction_updated(
    router: EventRouter,
    probes: ProbesDictionary,
):
    transaction_updated = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(UpdateTransactionReadModel(), TransactionUpdated),
                    EvictWalletCache(TransactionUpdated),
                    EvictTransactionCache(TransactionUpdated),
                    BumpTransactionListVersion(TransactionUpdated),
                    BumpWalletListVersion(TransactionUpdated),
                ]
            ),
            SyncProcessGroup([TrackEsAppliedSeq(UpdateTransactionDocument(), TransactionUpdated)]),
        ]
    )

    router.register(
        "TransactionUpdated",
        guard_all(transaction_updated, probes),
    )

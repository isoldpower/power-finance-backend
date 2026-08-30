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
    UpdateTransactionMetadataDocument,
    UpdateTransactionMetadataReadModel,
    UpdateTransactionReadModel,
)
from kafka_consumer_py import (
    EventRouter,
    ExecutionPlan,
    SyncProcessGroup,
)
from kafka_messages import (
    TransactionCreated,
    TransactionDeleted,
    TransactionMetadataUpdated,
    TransactionUpdated,
)

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


def subscribe_transaction_metadata_updated(
    router: EventRouter,
    probes: ProbesDictionary,
):
    metadata_updated = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(
                        UpdateTransactionMetadataReadModel(),
                        TransactionMetadataUpdated,
                    ),
                    EvictTransactionCache(TransactionMetadataUpdated),
                    BumpTransactionListVersion(TransactionMetadataUpdated),
                ]
            ),
            SyncProcessGroup(
                [
                    TrackEsAppliedSeq(
                        UpdateTransactionMetadataDocument(),
                        TransactionMetadataUpdated,
                    )
                ]
            ),
        ]
    )

    router.register(
        "TransactionMetadataUpdated",
        guard_all(metadata_updated, probes),
    )

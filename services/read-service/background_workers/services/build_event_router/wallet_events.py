from data_read_core.write_reactions import (
    BumpTransactionListVersion,
    BumpWalletListVersion,
    CreateWalletReadModel,
    EvictWalletCache,
    IndexWalletDocument,
    RemoveWalletDocument,
    RemoveWalletReadModel,
    RenameWalletInTransactions,
    TrackAppliedSeq,
    TrackEsAppliedSeq,
    UpdateWalletDocument,
    UpdateWalletReadModel,
)
from kafka_consumer_py import (
    EventRouter,
    ExecutionPlan,
    SyncProcessGroup,
)
from kafka_messages import (
    WalletCreated,
    WalletDeleted,
    WalletUpdated,
)

from ._health_guards import guard_all
from ._types import ProbesDictionary


def subscribe_wallet_deleted(
    router: EventRouter,
    probes: ProbesDictionary,
):
    wallet_deleted = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(RemoveWalletReadModel(), WalletDeleted),
                    EvictWalletCache(),
                    BumpWalletListVersion(WalletDeleted),
                ],
                atomic=True,
            ),
            SyncProcessGroup(
                [TrackEsAppliedSeq(RemoveWalletDocument(), WalletDeleted)], atomic=True
            ),
        ]
    )

    router.register(
        "WalletDeleted",
        guard_all(wallet_deleted, probes),
    )


def subscribe_wallet_updated(
    router: EventRouter,
    probes: ProbesDictionary,
):
    wallet_updated = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(UpdateWalletReadModel(), WalletUpdated),
                    RenameWalletInTransactions(),
                    EvictWalletCache(WalletUpdated),
                    BumpWalletListVersion(WalletUpdated),
                    BumpTransactionListVersion(WalletUpdated),
                ],
                atomic=True,
            ),
            SyncProcessGroup(
                [TrackEsAppliedSeq(UpdateWalletDocument(), WalletUpdated)], atomic=True
            ),
        ]
    )

    router.register(
        "WalletUpdated",
        guard_all(wallet_updated, probes),
    )


def subscribe_wallet_created(
    router: EventRouter,
    probes: ProbesDictionary,
):
    wallet_created = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(CreateWalletReadModel(), WalletCreated),
                    BumpWalletListVersion(WalletCreated),
                ],
                atomic=True,
            ),
            SyncProcessGroup(
                [TrackEsAppliedSeq(IndexWalletDocument(), WalletCreated)], atomic=True
            ),
        ]
    )

    router.register(
        "WalletCreated",
        guard_all(wallet_created, probes),
    )

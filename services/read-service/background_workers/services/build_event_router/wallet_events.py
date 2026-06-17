from data_read_core.shared.kafka_updates import (
    EventRouter,
    ExecutionPlan,
    SyncProcessGroup,
)
from data_read_core.write_reactions import (
    BumpWalletListVersion,
    CreateWalletReadModel,
    EvictWalletCache,
    IndexWalletDocument,
    RemoveWalletDocument,
    RemoveWalletReadModel,
    TrackAppliedSeq,
    TrackEsAppliedSeq,
    UpdateWalletDocument,
    UpdateWalletReadModel,
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
                ]
            ),
            SyncProcessGroup([TrackEsAppliedSeq(RemoveWalletDocument(), WalletDeleted)]),
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
                    EvictWalletCache(WalletUpdated),
                    BumpWalletListVersion(WalletUpdated),
                ]
            ),
            SyncProcessGroup([TrackEsAppliedSeq(UpdateWalletDocument(), WalletUpdated)]),
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
                ]
            ),
            SyncProcessGroup([TrackEsAppliedSeq(IndexWalletDocument(), WalletCreated)]),
        ]
    )

    router.register(
        "WalletCreated",
        guard_all(wallet_created, probes),
    )

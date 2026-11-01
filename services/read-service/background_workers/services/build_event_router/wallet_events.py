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
    ExecutionPlan,
    SyncProcessGroup,
)
from kafka_messages import (
    WalletCreated,
    WalletDeleted,
    WalletUpdated,
)

from ._health_guards import guard_postgres_lane, guard_search_lane
from ._types import ProbesDictionary, ProjectionRouters


def subscribe_wallet_deleted(
    routers: ProjectionRouters,
    probes: ProbesDictionary,
):
    postgres_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(RemoveWalletReadModel(), WalletDeleted),
                    EvictWalletCache(),
                    BumpWalletListVersion(WalletDeleted),
                ],
                atomic=True,
            ),
        ]
    )
    search_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [TrackEsAppliedSeq(RemoveWalletDocument(), WalletDeleted)], atomic=True
            ),
        ]
    )

    routers.postgres.register("WalletDeleted", guard_postgres_lane(postgres_plan, probes))
    routers.search.register("WalletDeleted", guard_search_lane(search_plan, probes, WalletDeleted))


def subscribe_wallet_updated(
    routers: ProjectionRouters,
    probes: ProbesDictionary,
):
    postgres_plan = ExecutionPlan(
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
        ]
    )
    search_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [TrackEsAppliedSeq(UpdateWalletDocument(), WalletUpdated)], atomic=True
            ),
        ]
    )

    routers.postgres.register("WalletUpdated", guard_postgres_lane(postgres_plan, probes))
    routers.search.register("WalletUpdated", guard_search_lane(search_plan, probes, WalletUpdated))


def subscribe_wallet_created(
    routers: ProjectionRouters,
    probes: ProbesDictionary,
):
    postgres_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(CreateWalletReadModel(), WalletCreated),
                    BumpWalletListVersion(WalletCreated),
                ],
                atomic=True,
            ),
        ]
    )
    search_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [TrackEsAppliedSeq(IndexWalletDocument(), WalletCreated)], atomic=True
            ),
        ]
    )

    routers.postgres.register("WalletCreated", guard_postgres_lane(postgres_plan, probes))
    routers.search.register("WalletCreated", guard_search_lane(search_plan, probes, WalletCreated))

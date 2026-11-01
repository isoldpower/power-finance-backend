from data_read_core.write_reactions import (
    AdjustContainerAmountOnCreate,
    AdjustContainerAmountOnDelete,
    AdjustContainerAmountOnUpdate,
    BumpGoalListVersion,
    BumpTransactionListVersion,
    BumpWalletListVersion,
    CreateTransactionReadModel,
    EvictGoalCacheForContainer,
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
    ExecutionPlan,
    SyncProcessGroup,
)
from kafka_messages import (
    TransactionCreated,
    TransactionDeleted,
    TransactionMetadataUpdated,
    TransactionUpdated,
)

from ._health_guards import guard_postgres_lane, guard_search_lane
from ._types import ProbesDictionary, ProjectionRouters


def subscribe_transaction_created(
    routers: ProjectionRouters,
    probes: ProbesDictionary,
):
    postgres_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(CreateTransactionReadModel(), TransactionCreated),
                    EvictWalletCache(TransactionCreated),
                    BumpTransactionListVersion(TransactionCreated),
                    BumpWalletListVersion(TransactionCreated),
                    EvictGoalCacheForContainer(TransactionCreated),
                    BumpGoalListVersion(TransactionCreated),
                ],
                atomic=True,
            ),
        ]
    )
    search_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    AdjustContainerAmountOnCreate(),
                    TrackEsAppliedSeq(IndexTransactionDocument(), TransactionCreated),
                ],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register("TransactionCreated", guard_postgres_lane(postgres_plan, probes))
    routers.search.register("TransactionCreated", guard_search_lane(search_plan, probes))


def subscribe_transaction_deleted(
    routers: ProjectionRouters,
    probes: ProbesDictionary,
):
    postgres_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(RemoveTransactionReadModel(), TransactionDeleted),
                    EvictWalletCache(TransactionDeleted),
                    EvictTransactionCache(TransactionDeleted),
                    BumpTransactionListVersion(TransactionDeleted),
                    BumpWalletListVersion(TransactionDeleted),
                    EvictGoalCacheForContainer(TransactionDeleted),
                    BumpGoalListVersion(TransactionDeleted),
                ],
                atomic=True,
            ),
        ]
    )
    search_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    AdjustContainerAmountOnDelete(),
                    TrackEsAppliedSeq(RemoveTransactionDocument(), TransactionDeleted),
                ],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register("TransactionDeleted", guard_postgres_lane(postgres_plan, probes))
    routers.search.register("TransactionDeleted", guard_search_lane(search_plan, probes))


def subscribe_transaction_updated(
    routers: ProjectionRouters,
    probes: ProbesDictionary,
):
    postgres_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(UpdateTransactionReadModel(), TransactionUpdated),
                    EvictWalletCache(TransactionUpdated),
                    EvictTransactionCache(TransactionUpdated),
                    BumpTransactionListVersion(TransactionUpdated),
                    BumpWalletListVersion(TransactionUpdated),
                    EvictGoalCacheForContainer(TransactionUpdated),
                    BumpGoalListVersion(TransactionUpdated),
                ],
                atomic=True,
            ),
        ]
    )
    search_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    AdjustContainerAmountOnUpdate(),
                    TrackEsAppliedSeq(UpdateTransactionDocument(), TransactionUpdated),
                ],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register("TransactionUpdated", guard_postgres_lane(postgres_plan, probes))
    routers.search.register("TransactionUpdated", guard_search_lane(search_plan, probes))


def subscribe_transaction_metadata_updated(
    routers: ProjectionRouters,
    probes: ProbesDictionary,
):
    postgres_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(
                        UpdateTransactionMetadataReadModel(),
                        TransactionMetadataUpdated,
                    ),
                    EvictTransactionCache(TransactionMetadataUpdated),
                    BumpTransactionListVersion(TransactionMetadataUpdated),
                ],
                atomic=True,
            ),
        ]
    )
    search_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackEsAppliedSeq(
                        UpdateTransactionMetadataDocument(),
                        TransactionMetadataUpdated,
                    )
                ],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register(
        "TransactionMetadataUpdated", guard_postgres_lane(postgres_plan, probes)
    )
    routers.search.register("TransactionMetadataUpdated", guard_search_lane(search_plan, probes))

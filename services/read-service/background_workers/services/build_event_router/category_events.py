from data_read_core.write_reactions import (
    BumpCategoryListVersion,
    BumpTransactionListVersion,
    BumpWalletListVersion,
    CreateCategoryReadModel,
    EvictCategorisedItemCaches,
    RemoveCategoryReadModel,
    RenameCategoryInDocuments,
    RenameCategoryReadModel,
    TrackAppliedSeq,
    TrackEsAppliedSeq,
)
from kafka_consumer_py import (
    ExecutionPlan,
    SyncProcessGroup,
)
from kafka_messages import (
    CategoryCreated,
    CategoryDeleted,
    CategoryUpdated,
)

from ._health_guards import guard_postgres_lane, guard_search_lane, guard_search_watermark_lane
from ._types import ProbesDictionary, ProjectionRouters


def subscribe_category_created(routers: ProjectionRouters, probes: ProbesDictionary):
    postgres_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(CreateCategoryReadModel(), CategoryCreated),
                    BumpCategoryListVersion(CategoryCreated),
                ],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register("CategoryCreated", guard_postgres_lane(postgres_plan, probes))
    routers.search.register(
        "CategoryCreated",
        guard_search_watermark_lane(CategoryCreated, probes),
    )


def subscribe_category_updated(routers: ProjectionRouters, probes: ProbesDictionary):
    postgres_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(RenameCategoryReadModel(), CategoryUpdated),
                    BumpCategoryListVersion(CategoryUpdated),
                    EvictCategorisedItemCaches(),
                    BumpWalletListVersion(CategoryUpdated),
                    BumpTransactionListVersion(CategoryUpdated),
                ],
                atomic=True,
            ),
        ]
    )
    search_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [TrackEsAppliedSeq(RenameCategoryInDocuments(), CategoryUpdated)],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register("CategoryUpdated", guard_postgres_lane(postgres_plan, probes))
    routers.search.register(
        "CategoryUpdated",
        guard_search_lane(search_plan, probes, CategoryUpdated),
    )


def subscribe_category_deleted(routers: ProjectionRouters, probes: ProbesDictionary):
    postgres_plan = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(RemoveCategoryReadModel(), CategoryDeleted),
                    BumpCategoryListVersion(CategoryDeleted),
                ],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register("CategoryDeleted", guard_postgres_lane(postgres_plan, probes))
    routers.search.register(
        "CategoryDeleted",
        guard_search_watermark_lane(CategoryDeleted, probes),
    )

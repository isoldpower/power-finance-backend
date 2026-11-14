from data_read_core.write_reactions import (
    BumpWebhookListVersion,
    CreateWebhookReadModel,
    CreateWebhookSubscriptionReadModel,
    EvictWebhookCache,
    EvictWebhookEventsCache,
    RemoveWebhookReadModel,
    RemoveWebhookSubscriptionReadModel,
    TrackAppliedSeq,
    UpdateWebhookReadModel,
)
from kafka_consumer_py import (
    ExecutionPlan,
    SyncProcessGroup,
)
from kafka_messages import (
    WebhookEndpointCreated,
    WebhookEndpointDeleted,
    WebhookEndpointUpdated,
    WebhookSubscriptionAdded,
    WebhookSubscriptionRemoved,
)

from ._health_guards import guard_postgres_lane, guard_search_watermark_lane
from ._types import ProbesDictionary, ProjectionRouters


def subscribe_webhook_created(
    routers: ProjectionRouters,
    probes: ProbesDictionary,
):
    webhook_created = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(CreateWebhookReadModel(), WebhookEndpointCreated),
                    BumpWebhookListVersion(WebhookEndpointCreated),
                ],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register(
        "WebhookEndpointCreated",
        guard_postgres_lane(webhook_created, probes),
    )
    routers.search.register(
        "WebhookEndpointCreated",
        guard_search_watermark_lane(WebhookEndpointCreated, probes),
    )


def subscribe_webhook_updated(
    routers: ProjectionRouters,
    probes: ProbesDictionary,
):
    webhook_updated = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(UpdateWebhookReadModel(), WebhookEndpointUpdated),
                    EvictWebhookCache(WebhookEndpointUpdated),
                    BumpWebhookListVersion(WebhookEndpointUpdated),
                ],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register(
        "WebhookEndpointUpdated",
        guard_postgres_lane(webhook_updated, probes),
    )
    routers.search.register(
        "WebhookEndpointUpdated",
        guard_search_watermark_lane(WebhookEndpointUpdated, probes),
    )


def subscribe_webhook_deleted(
    routers: ProjectionRouters,
    probes: ProbesDictionary,
):
    webhook_deleted = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(RemoveWebhookReadModel(), WebhookEndpointDeleted),
                    EvictWebhookCache(WebhookEndpointDeleted),
                    EvictWebhookEventsCache(WebhookEndpointDeleted),
                    BumpWebhookListVersion(WebhookEndpointDeleted),
                ],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register(
        "WebhookEndpointDeleted",
        guard_postgres_lane(webhook_deleted, probes),
    )
    routers.search.register(
        "WebhookEndpointDeleted",
        guard_search_watermark_lane(WebhookEndpointDeleted, probes),
    )


def subscribe_webhook_subscription_added(
    routers: ProjectionRouters,
    probes: ProbesDictionary,
):
    subscription_added = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(
                        CreateWebhookSubscriptionReadModel(),
                        WebhookSubscriptionAdded,
                    ),
                    EvictWebhookEventsCache(WebhookSubscriptionAdded),
                ],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register(
        "WebhookSubscriptionAdded",
        guard_postgres_lane(subscription_added, probes),
    )
    routers.search.register(
        "WebhookSubscriptionAdded",
        guard_search_watermark_lane(WebhookSubscriptionAdded, probes),
    )


def subscribe_webhook_subscription_removed(
    routers: ProjectionRouters,
    probes: ProbesDictionary,
):
    subscription_removed = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(
                        RemoveWebhookSubscriptionReadModel(),
                        WebhookSubscriptionRemoved,
                    ),
                    EvictWebhookEventsCache(WebhookSubscriptionRemoved),
                ],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register(
        "WebhookSubscriptionRemoved",
        guard_postgres_lane(subscription_removed, probes),
    )
    routers.search.register(
        "WebhookSubscriptionRemoved",
        guard_search_watermark_lane(WebhookSubscriptionRemoved, probes),
    )

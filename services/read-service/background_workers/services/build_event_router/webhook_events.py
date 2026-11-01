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

from ._health_guards import guard_postgres_lane
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

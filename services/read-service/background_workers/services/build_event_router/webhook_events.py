from data_read_core.shared.kafka_updates import (
    EventRouter,
    ExecutionPlan,
    SyncProcessGroup,
)
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
from kafka_messages import (
    WebhookEndpointCreated,
    WebhookEndpointDeleted,
    WebhookEndpointUpdated,
    WebhookSubscriptionAdded,
    WebhookSubscriptionRemoved,
)

from ._health_guards import guard_all
from ._types import ProbesDictionary


def subscribe_webhook_created(
    router: EventRouter,
    probes: ProbesDictionary,
):
    webhook_created = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(CreateWebhookReadModel(), WebhookEndpointCreated),
                    BumpWebhookListVersion(WebhookEndpointCreated),
                ]
            ),
        ]
    )

    router.register(
        "WebhookEndpointCreated",
        guard_all(webhook_created, probes),
    )


def subscribe_webhook_updated(
    router: EventRouter,
    probes: ProbesDictionary,
):
    webhook_updated = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(UpdateWebhookReadModel(), WebhookEndpointUpdated),
                    EvictWebhookCache(WebhookEndpointUpdated),
                    BumpWebhookListVersion(WebhookEndpointUpdated),
                ]
            ),
        ]
    )

    router.register(
        "WebhookEndpointUpdated",
        guard_all(webhook_updated, probes),
    )


def subscribe_webhook_deleted(
    router: EventRouter,
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
                ]
            ),
        ]
    )

    router.register(
        "WebhookEndpointDeleted",
        guard_all(webhook_deleted, probes),
    )


def subscribe_webhook_subscription_added(
    router: EventRouter,
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
                ]
            ),
        ]
    )

    router.register(
        "WebhookSubscriptionAdded",
        guard_all(subscription_added, probes),
    )


def subscribe_webhook_subscription_removed(
    router: EventRouter,
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
                ]
            ),
        ]
    )

    router.register(
        "WebhookSubscriptionRemoved",
        guard_all(subscription_removed, probes),
    )

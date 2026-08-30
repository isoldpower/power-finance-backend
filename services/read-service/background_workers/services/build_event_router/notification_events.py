from data_read_core.write_reactions import (
    AcknowledgeNotificationReadModels,
    BumpNotificationListVersion,
    CreateNotificationReadModel,
    EvictAcknowledgedNotificationsCache,
    EvictNotificationCache,
    RemoveNotificationReadModel,
    TrackAppliedSeq,
)
from kafka_consumer_py import (
    EventRouter,
    ExecutionPlan,
    SyncProcessGroup,
)
from kafka_messages import (
    NotificationCreated,
    NotificationDeleted,
    NotificationsAcknowledged,
)

from ._health_guards import guard_all
from ._types import ProbesDictionary


def subscribe_notification_created(
    router: EventRouter,
    probes: ProbesDictionary,
):
    notification_created = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(CreateNotificationReadModel(), NotificationCreated),
                    BumpNotificationListVersion(NotificationCreated),
                ]
            ),
        ]
    )

    router.register(
        "NotificationCreated",
        guard_all(notification_created, probes),
    )


def subscribe_notifications_acknowledged(
    router: EventRouter,
    probes: ProbesDictionary,
):
    notifications_acknowledged = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(
                        AcknowledgeNotificationReadModels(),
                        NotificationsAcknowledged,
                    ),
                    EvictAcknowledgedNotificationsCache(),
                    BumpNotificationListVersion(NotificationsAcknowledged),
                ]
            ),
        ]
    )

    router.register(
        "NotificationsAcknowledged",
        guard_all(notifications_acknowledged, probes),
    )


def subscribe_notification_deleted(
    router: EventRouter,
    probes: ProbesDictionary,
):
    notification_deleted = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(RemoveNotificationReadModel(), NotificationDeleted),
                    EvictNotificationCache(),
                    BumpNotificationListVersion(NotificationDeleted),
                ]
            ),
        ]
    )

    router.register(
        "NotificationDeleted",
        guard_all(notification_deleted, probes),
    )

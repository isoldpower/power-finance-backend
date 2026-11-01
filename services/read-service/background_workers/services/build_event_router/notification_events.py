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
    ExecutionPlan,
    SyncProcessGroup,
)
from kafka_messages import (
    NotificationCreated,
    NotificationDeleted,
    NotificationsAcknowledged,
)

from ._health_guards import guard_postgres_lane
from ._types import ProbesDictionary, ProjectionRouters


def subscribe_notification_created(
    routers: ProjectionRouters,
    probes: ProbesDictionary,
):
    notification_created = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(CreateNotificationReadModel(), NotificationCreated),
                    BumpNotificationListVersion(NotificationCreated),
                ],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register(
        "NotificationCreated",
        guard_postgres_lane(notification_created, probes),
    )


def subscribe_notifications_acknowledged(
    routers: ProjectionRouters,
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
                ],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register(
        "NotificationsAcknowledged",
        guard_postgres_lane(notifications_acknowledged, probes),
    )


def subscribe_notification_deleted(
    routers: ProjectionRouters,
    probes: ProbesDictionary,
):
    notification_deleted = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(RemoveNotificationReadModel(), NotificationDeleted),
                    EvictNotificationCache(),
                    BumpNotificationListVersion(NotificationDeleted),
                ],
                atomic=True,
            ),
        ]
    )

    routers.postgres.register(
        "NotificationDeleted",
        guard_postgres_lane(notification_deleted, probes),
    )

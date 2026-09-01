from datetime import UTC, datetime
from uuid import UUID

import pytest

from data_write_core.application.commands import (
    AcknowledgeNotificationsCommand,
    AcknowledgeNotificationsCommandHandler,
)
from data_write_core.domain.entities import NotificationEntity
from data_write_core.domain.exceptions import NotificationNotFoundError

NOTIFICATION_A = "11111111-1111-1111-1111-111111111111"
NOTIFICATION_MISSING = "22222222-2222-2222-2222-222222222222"


FIRST_SEEN_AT = datetime(2026, 1, 2, tzinfo=UTC)


def make_notification(
    notification_id: str,
    *,
    acknowledged_at: datetime | None = None,
) -> NotificationEntity:
    return NotificationEntity(
        id=notification_id,
        title="title",
        body="body",
        user_id="7",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        acknowledged_at=acknowledged_at,
    )


class FakeNotificationRepository:
    def __init__(self, notifications: list[NotificationEntity]) -> None:
        self._notifications = notifications

    async def get_user_notifications_by_ids(self, notification_ids, user_id):
        requested = {str(notification_id) for notification_id in notification_ids}
        return [
            notification
            for notification in self._notifications
            if str(notification.unique_id) in requested
        ]


class FakeOutboxRepository:
    async def get_latest_sequence(self) -> int:
        return 42


async def test_ack_of_an_already_read_notification_returns_it_unchanged():
    """Idempotent by nature: the caller's intent is already satisfied, so this
    is a 200 carrying the original `acknowledged_at`, never a conflict."""

    handler = AcknowledgeNotificationsCommandHandler(
        notification_repository=FakeNotificationRepository(
            [make_notification(NOTIFICATION_A, acknowledged_at=FIRST_SEEN_AT)],
        ),
        outbox_repository=FakeOutboxRepository(),
    )

    acknowledged, write_version = await handler.handle(
        AcknowledgeNotificationsCommand(
            user_id=7,
            user_external_id="user_abc",
            notification_ids=(UUID(NOTIFICATION_A),),
        )
    )

    assert [notification.acknowledged_at for notification in acknowledged] == [FIRST_SEEN_AT]
    assert write_version == 42


async def test_strict_ack_raises_for_unknown_id():
    handler = AcknowledgeNotificationsCommandHandler(
        notification_repository=FakeNotificationRepository(
            [make_notification(NOTIFICATION_A)],
        ),
        outbox_repository=FakeOutboxRepository(),
    )

    with pytest.raises(NotificationNotFoundError):
        await handler.handle(
            AcknowledgeNotificationsCommand(
                user_id=7,
                user_external_id="user_abc",
                notification_ids=(UUID(NOTIFICATION_MISSING),),
                strict=True,
            )
        )

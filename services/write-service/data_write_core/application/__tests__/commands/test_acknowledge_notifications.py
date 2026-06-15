from datetime import datetime
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


def make_notification(notification_id: str, *, is_read: bool = False) -> NotificationEntity:
    return NotificationEntity(
        id=notification_id,
        short="short",
        message="message",
        user_id="7",
        created_at=datetime(2026, 1, 1),
        is_read=is_read,
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


async def test_ack_skips_already_read_without_emitting():
    handler = AcknowledgeNotificationsCommandHandler(
        notification_repository=FakeNotificationRepository(
            [make_notification(NOTIFICATION_A, is_read=True)],
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

    assert acknowledged == []
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

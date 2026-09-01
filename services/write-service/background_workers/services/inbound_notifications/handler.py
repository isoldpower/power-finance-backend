import json
import logging

from data_write_core.application.commands import (
    CreateNotificationCommand,
    CreateNotificationCommandHandler,
)
from data_write_core.infrastructure.messaging import normalise_severity
from kafka_client_py import ConsumedMessage, PoisonError

logger = logging.getLogger("background_workers.inbound_notifications")


def _parse_notification_request(message: ConsumedMessage) -> CreateNotificationCommand:
    if message.value is None:
        raise PoisonError("Empty message on the inbound notifications topic")

    try:
        request = json.loads(message.value)
        subject = request.get("subject") or {}

        return CreateNotificationCommand(
            user_id=int(request["user_id"]),
            user_external_id=str(request["user_external_id"]),
            title=str(request["title"]),
            body=str(request["body"]),
            payload=request.get("payload") or None,
            severity=normalise_severity(request.get("severity")),
            subject_type=str(subject["type"]) if subject.get("type") else None,
            subject_id=str(subject["id"]) if subject.get("id") else None,
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise PoisonError(f"Malformed NotificationRequested message: {exc}") from exc


async def handle_notification_request(message: ConsumedMessage) -> None:
    command = _parse_notification_request(message)
    await CreateNotificationCommandHandler().handle(command)

    logger.info(
        "inbound_notifications: created notification for user_id=%s (title=%r)",
        command.user_id,
        command.title,
    )

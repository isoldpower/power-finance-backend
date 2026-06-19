import json
import logging

from data_write_core.application.commands import (
    CreateNotificationCommand,
    CreateNotificationCommandHandler,
)
from kafka_client_py import ConsumedMessage, PoisonError

logger = logging.getLogger("background_workers.inbound_notifications")


def _parse_notification_request(message: ConsumedMessage) -> CreateNotificationCommand:
    if message.value is None:
        raise PoisonError("Empty message on the inbound notifications topic")

    try:
        request = json.loads(message.value)
        return CreateNotificationCommand(
            user_id=int(request["user_id"]),
            user_external_id=str(request["user_external_id"]),
            short=str(request["short"]),
            message=str(request["message"]),
            payload=request.get("payload") or None,
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise PoisonError(f"Malformed NotificationRequested message: {exc}") from exc


async def handle_notification_request(message: ConsumedMessage) -> None:
    command = _parse_notification_request(message)
    await CreateNotificationCommandHandler().handle(command)
    logger.info(
        "inbound_notifications: created notification for user_id=%s (short=%r)",
        command.user_id,
        command.short,
    )

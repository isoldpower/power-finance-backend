from uuid import uuid4
from queue import Empty

from .format_sse import format_sse

from finances.application.interfaces import NotificationChannel


def get_latest_message(channel: NotificationChannel) -> tuple[str | None, str]:
    try:
        notification_payload = channel.get(timeout=15, block=True)
        notification_id = str(notification_payload.get("id"))
        return (notification_id, format_sse(
            event="notification",
            event_id=notification_id,
            data=notification_payload,
        ))
    except Empty:
        return (None, format_sse(
            event="ping",
            event_id=str(uuid4()),
            data={
                "ok": True,
                "message": "Connection keep-alive."
            }
        ))
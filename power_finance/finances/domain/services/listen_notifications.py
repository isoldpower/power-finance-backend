import asyncio
from uuid import uuid4

from .format_sse import format_sse

from finances.application.interfaces import NotificationChannel


async def get_latest_message(
        channel: NotificationChannel
) -> tuple[str | None, str]:
    try:
        notification_payload = await channel.get(timeout=15.0)
        notification_id = str(notification_payload.get("id"))
        return (notification_id, format_sse(
            event="notification",
            event_id=notification_id,
            data=notification_payload,
        ))
    except asyncio.TimeoutError:
        return (None, format_sse(
            event="ping",
            event_id=str(uuid4()),
            data={
                "ok": True,
                "message": "Connection keep-alive."
            }
        ))
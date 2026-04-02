from uuid import uuid4
from dataclasses import asdict
from queue import Empty

from .format_sse import format_sse

from finances.application.interfaces import NotificationBroker


def listen_notifications(broker: NotificationBroker, user_id: int):
    subscription = broker.subscribe(user_id)

    try:
        yield format_sse(
            event="connected",
            event_id=str(uuid4()),
            data={
                "ok": True,
                "message": "SSE connection established."
            },
        )

        while True:
            try:
                notification_payload = subscription.get(timeout=15, block=True)
                yield format_sse(
                    event="notification",
                    event_id=str(notification_payload.get("id")),
                    data=notification_payload,
                )
            except Empty:
                yield format_sse(
                    event="ping",
                    event_id=str(uuid4()),
                    data={
                        "ok": True,
                        "message": "Connection keep-alive."
                    }
                )
    except GeneratorExit:
        pass
    finally:
        broker.unsubscribe(user_id, subscription)
import asyncio
from dataclasses import dataclass
from uuid import uuid4

from finances.domain.services import format_sse, get_latest_message

from ...interfaces import NotificationBroker


@dataclass(frozen=True)
class OpenNotificationsConnection:
    user_id: int


class OpenNotificationsConnectionHandler:
    def __init__(
            self,
            notification_broker: NotificationBroker,
    ) -> None:
        self._broker = notification_broker

    async def handle(self, command: OpenNotificationsConnection):
        subscription = await self._broker.subscribe(command.user_id)

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
                # get_latest_message is async
                notification_id, message = await get_latest_message(subscription)
                yield message
        except GeneratorExit:
            pass
        finally:
            await self._broker.unsubscribe(command.user_id, subscription)
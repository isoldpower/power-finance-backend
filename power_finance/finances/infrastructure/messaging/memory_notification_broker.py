import asyncio
from collections import defaultdict
from typing import DefaultDict

from finances.application.interfaces import (
    NotificationBroker,
    NotificationChannel,
)


class InMemoryNotificationChannel(NotificationChannel):
    def __init__(self, queue: asyncio.Queue) -> None:
        self._queue = queue

    async def get(self, timeout: float | None = None) -> dict:
        try:
            if timeout:
                return await asyncio.wait_for(self._queue.get(), timeout=timeout)
            return await self._queue.get()
        except asyncio.TimeoutError:
            raise


class InMemoryNotificationBroker(NotificationBroker):
    def __init__(self) -> None:
        self._subscriptions: DefaultDict[int, list[tuple[InMemoryNotificationChannel, asyncio.Queue]]] = defaultdict(list)

    async def subscribe(self, user_id: int) -> InMemoryNotificationChannel:
        queue = asyncio.Queue()
        channel = InMemoryNotificationChannel(queue)
        self._subscriptions[user_id].append((channel, queue))
        
        return channel

    async def unsubscribe(self, user_id: int, channel: NotificationChannel) -> None:
        subscriptions = self._subscriptions.get(user_id, [])
        for i, (sub_channel, sub_queue) in enumerate(subscriptions):
            if sub_channel is channel:
                subscriptions.pop(i)
                break
        
        if not subscriptions and user_id in self._subscriptions:
            del self._subscriptions[user_id]

    async def publish(self, user_id: int, payload: dict) -> None:
        subscriptions = self._subscriptions.get(user_id, [])
        for _, queue in subscriptions:
            await queue.put(payload)
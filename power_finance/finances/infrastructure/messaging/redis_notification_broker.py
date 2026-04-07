import asyncio
import json
from redis.asyncio.client import PubSub, Redis

from finances.application.interfaces import (
    NotificationBroker,
    NotificationChannel,
)


class RedisChannelWrapper(NotificationChannel):
    _closed: bool = False

    def __init__(self, pubsub: PubSub, channel_id: str) -> None:
        self._channel_id = channel_id
        self._pubsub = pubsub

    @classmethod
    async def create(cls, redis_client: Redis, channel_id: str) -> 'RedisChannelWrapper':
        pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
        await pubsub.subscribe(channel_id)

        return cls(pubsub=pubsub, channel_id=channel_id)

    async def close(self) -> None:
        if self._closed:
            return

        self._closed = True
        await self._pubsub.unsubscribe(self._channel_id)
        await self._pubsub.close()

    async def get(self, timeout: float | None = None) -> dict:
        if self._closed:
            raise ConnectionRefusedError("Trying to read value from channel that is closed.")

        received_message = await self._pubsub.get_message(
            ignore_subscribe_messages=True,
            timeout=timeout
        )
        if received_message is None:
            raise asyncio.TimeoutError("Didn't receive any message in specified timeout period.")

        data = received_message.get("data")
        if isinstance(data, (bytes, bytearray)):
            data = data.decode("utf-8")
        return json.loads(data)


class RedisNotificationBroker(NotificationBroker):
    def __init__(self, redis_client: Redis) -> None:
        self._redis_client = redis_client

    def _get_channel_id(self, user_id: int) -> str:
        return f"notifications:user:{user_id}"

    async def subscribe(self, user_id: int) -> RedisChannelWrapper:
        channel_id = self._get_channel_id(user_id)
        return await RedisChannelWrapper.create(self._redis_client, channel_id)

    async def unsubscribe(self, user_id: int, channel: RedisChannelWrapper) -> None:
        await channel.close()

    async def publish(self, user_id: int, payload: dict) -> None:
        channel_id = self._get_channel_id(user_id)
        await self._redis_client.publish(channel_id, json.dumps(payload))
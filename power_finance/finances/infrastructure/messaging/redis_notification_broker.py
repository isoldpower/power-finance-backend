import json
from collections import defaultdict
from queue import Queue, Empty
from typing import DefaultDict
from redis.client import Redis, PubSub

from finances.application.interfaces import NotificationBroker, NotificationChannel


class RedisChannelWrapper(NotificationChannel):
    _closed: bool = False

    def __init__(
            self,
            pubsub: PubSub,
            channel_id: str
    ) -> None:
        self._channel_id = channel_id
        self._pubsub = pubsub

        self._pubsub.subscribe(channel_id)

    def __delete__(self, instance):
        self._pubsub.unsubscribe(self._channel_id)

    def __del__(self):
        self._closed = True

    def get(
            self,
            block: bool = True,
            timeout: float | None = None
    ) -> dict:
        if self._closed:
            raise ConnectionRefusedError("Trying to read value from channel that is closed.")

        fallback_timeout = None if block else 0.0
        message = self._pubsub.get_message(timeout=timeout or fallback_timeout)

        if message is None:
            raise Empty()

        data = message.get("data")
        if isinstance(data, (bytes, bytearray)):
            data = data.decode("utf-8")

        return json.loads(data)


class RedisNotificationBroker(NotificationBroker):
    def __init__(
            self,
            redis_client: Redis
    ) -> None:
        self._subscriptions: DefaultDict[int, list[Queue]] = defaultdict(list)
        self._redis_client = redis_client
        self._pubsub = self._redis_client.pubsub(ignore_subscribe_messages=True)

    def _get_channel_id(self, user_id: int) -> str:
        return f"notifications:user:{user_id}"

    def subscribe(self, user_id: int) -> RedisChannelWrapper:
        channel_id = self._get_channel_id(user_id)

        return RedisChannelWrapper(self._pubsub, channel_id)

    def unsubscribe(self, user_id: int, channel: RedisChannelWrapper) -> None:
        del channel

    def publish(self, user_id: int, payload: dict) -> None:
        channel_id = self._get_channel_id(user_id)
        self._redis_client.publish(channel_id, json.dumps(payload))
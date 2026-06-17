import json

from redis.asyncio import Redis

from .dtos import NotificationDTO
from .infra import (
    CACHE_TTL_SECONDS,
    get_single_cache_key,
)


class CacheWorker:
    def __init__(self, redis_client: Redis) -> None:
        self._redis_client = redis_client

    async def try_serve_from_cache(
        self,
        notification_id: str,
        user_id: int,
    ) -> NotificationDTO | None:
        cache_key = get_single_cache_key(notification_id)
        cached_value = await self._redis_client.get(cache_key)
        if cached_value is None:
            return None

        notification = NotificationDTO.from_cache(json.loads(cached_value))
        if notification.user_id != user_id:
            await self._redis_client.delete(cache_key)
            return None

        return notification

    async def save_to_cache(self, notification: NotificationDTO) -> None:
        cache_key = get_single_cache_key(notification.id)
        await self._redis_client.set(
            cache_key,
            json.dumps(notification.to_cache()),
            ex=CACHE_TTL_SECONDS,
        )

import json

from redis.asyncio import Redis

from .dtos import WebhookSubscriptionDTO
from .infra import CACHE_TTL_SECONDS, get_events_cache_key


class CacheWorker:
    def __init__(self, redis_client: Redis) -> None:
        self._redis_client = redis_client

    async def try_serve_from_cache(
        self,
        webhook_id: str,
    ) -> list[WebhookSubscriptionDTO] | None:
        cached_value = await self._redis_client.get(get_events_cache_key(webhook_id))
        if cached_value is None:
            return None

        return [WebhookSubscriptionDTO.from_cache(item) for item in json.loads(cached_value)]

    async def save_to_cache(
        self,
        webhook_id: str,
        subscriptions: list[WebhookSubscriptionDTO],
    ) -> None:
        await self._redis_client.set(
            get_events_cache_key(webhook_id),
            json.dumps([subscription.to_cache() for subscription in subscriptions]),
            ex=CACHE_TTL_SECONDS,
        )

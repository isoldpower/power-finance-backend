import json

from redis.asyncio import Redis

from .dtos import CacheOperationData, WebhookDTO
from .infra import (
    CACHE_TTL_SECONDS,
    get_list_cache_key,
    get_list_version_key,
)


class CacheWorker:
    def __init__(self, redis_client: Redis) -> None:
        self._redis_client = redis_client

    async def try_serve_from_cache(
        self,
        context: CacheOperationData,
    ) -> tuple[list[WebhookDTO], int] | None:
        cache_key = await self._build_cache_key(context)

        return await self._try_retrieve_from_cache(cache_key)

    async def save_to_cache(
        self,
        context: CacheOperationData,
        webhooks: list[WebhookDTO],
        total: int,
    ) -> None:
        cache_key = await self._build_cache_key(context)
        payload = {
            "webhooks": [webhook.to_cache() for webhook in webhooks],
            "total": total,
        }

        await self._redis_client.set(
            cache_key,
            json.dumps(payload),
            ex=CACHE_TTL_SECONDS,
        )

    async def _build_cache_key(self, context: CacheOperationData) -> str:
        version = await self._current_version(context.user_id)

        return get_list_cache_key(
            user_id=context.user_id,
            version=version,
            limit=context.limit,
            cursor=context.cursor,
        )

    async def _current_version(self, user_id: int) -> int:
        raw_version = await self._redis_client.get(get_list_version_key(user_id))

        return int(raw_version) if raw_version is not None else 0

    async def _try_retrieve_from_cache(self, cache_key: str) -> tuple[list[WebhookDTO], int] | None:
        cached_value = await self._redis_client.get(cache_key)
        if cached_value is None:
            return None

        payload = json.loads(cached_value)
        webhooks = [WebhookDTO.from_cache(item) for item in payload["webhooks"]]
        return webhooks, payload["total"]

import json

from redis.asyncio import Redis

from .config import CacheSettings
from .dtos import CacheOperationData, CategoryDTO
from .infra import get_list_cache_key, get_list_version_key


class CacheWorker:
    def __init__(self, redis_client: Redis) -> None:
        self._redis_client = redis_client

    async def try_serve_from_cache(
        self,
        context: CacheOperationData,
    ) -> tuple[list[CategoryDTO], int] | None:
        cached_value = await self._redis_client.get(await self._build_cache_key(context))
        if cached_value is None:
            return None

        payload = json.loads(cached_value)
        return [CategoryDTO.from_cache(item) for item in payload["categories"]], payload["total"]

    async def save_to_cache(
        self,
        context: CacheOperationData,
        categories: list[CategoryDTO],
        total: int,
    ) -> None:
        payload = {
            "categories": [category.to_cache() for category in categories],
            "total": total,
        }

        await self._redis_client.set(
            await self._build_cache_key(context),
            json.dumps(payload),
            ex=int(CacheSettings.TTL_SECONDS),
        )

    async def _build_cache_key(self, context: CacheOperationData) -> str:
        raw_version = await self._redis_client.get(get_list_version_key(context.user_id))

        return get_list_cache_key(
            user_id=context.user_id,
            version=int(raw_version) if raw_version is not None else 0,
            kind=context.kind,
            limit=context.limit,
            cursor=context.cursor,
        )

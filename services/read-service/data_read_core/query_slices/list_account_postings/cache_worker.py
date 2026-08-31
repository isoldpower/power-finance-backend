import json

from redis.asyncio import Redis

from .dtos import AccountPostingDTO, CacheOperationData
from .infra import (
    CACHE_TTL_SECONDS,
    get_filter_hash,
    get_list_cache_key,
    get_list_version_key,
)


class CacheWorker:
    def __init__(self, redis_client: Redis) -> None:
        self._redis_client = redis_client

    async def try_serve_from_cache(
        self,
        context: CacheOperationData,
    ) -> tuple[list[AccountPostingDTO], int] | None:
        cache_key = await self._build_cache_key(context)

        return await self._try_retrieve_from_cache(cache_key)

    async def save_to_cache(
        self,
        context: CacheOperationData,
        postings: list[AccountPostingDTO],
        total: int,
    ) -> None:
        cache_key = await self._build_cache_key(context)
        payload = {
            "postings": [posting.to_cache() for posting in postings],
            "total": total,
        }

        await self._redis_client.set(
            cache_key,
            json.dumps(payload),
            ex=CACHE_TTL_SECONDS,
        )

    async def _build_cache_key(self, context: CacheOperationData) -> str:
        version = await self._current_version(context.account_id)

        return get_list_cache_key(
            account_id=context.account_id,
            version=version,
            filter_hash=get_filter_hash(context.filters),
            limit=context.limit,
            cursor=context.cursor,
        )

    async def _current_version(self, account_id: str) -> int:
        raw_version = await self._redis_client.get(
            get_list_version_key(account_id),
        )

        return int(raw_version) if raw_version is not None else 0

    async def _try_retrieve_from_cache(
        self,
        cache_key: str,
    ) -> tuple[list[AccountPostingDTO], int] | None:
        cached_value = await self._redis_client.get(cache_key)
        if cached_value is None:
            return None

        payload = json.loads(cached_value)
        postings = [AccountPostingDTO.from_cache(item) for item in payload["postings"]]
        return postings, payload["total"]

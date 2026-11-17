from redis.asyncio import Redis

from data_read_core.shared.query_results import FetchedRows

from .cache_worker import CacheWorker
from .dtos import CacheOperationData, CategoryDTO, ListCategoriesQuery
from .infra import count_visible_categories, fetch_visible_categories, get_redis_client
from .logger_shortcuts import log_served_from_cache, log_served_from_store


class ListCategoriesQueryHandler:
    def __init__(self, redis_client: Redis | None = None) -> None:
        self._cache_worker = CacheWorker(redis_client or get_redis_client())

    async def handle(self, query: ListCategoriesQuery) -> FetchedRows:
        cache_operation = CacheOperationData(
            user_id=query.user_id,
            kind=query.kind,
            limit=query.page.limit,
            cursor=query.page.cache_token,
        )
        cached_value = await self._cache_worker.try_serve_from_cache(cache_operation)
        if cached_value is not None:
            log_served_from_cache(query.user_id)
            return FetchedRows(rows=cached_value[0], total=cached_value[1], cached=True)

        total = await count_visible_categories(query.user_id, query.kind)
        categories = [
            CategoryDTO.from_read_model(category)
            for category in await fetch_visible_categories(query.user_id, query.kind, query.page)
        ]
        await self._cache_worker.save_to_cache(cache_operation, categories, total)

        log_served_from_store(query.user_id, len(categories), total)
        return FetchedRows(rows=categories, total=total, cached=False)

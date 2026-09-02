from redis.asyncio import Redis

from data_read_core.shared.query_results import FetchedRows

from .cache_worker import CacheWorker
from .dtos import AutomationDTO, CacheOperationData, ListAutomationsQuery
from .infra import count_owned_automations, fetch_owned_automations, get_redis_client
from .logger_shortcuts import log_served_from_cache, log_served_from_store


class ListAutomationsQueryHandler:
    def __init__(self, redis_client: Redis | None = None):
        redis_client = redis_client or get_redis_client()

        self._redis_client = redis_client
        self._cache_worker = CacheWorker(redis_client)

    async def handle(self, query: ListAutomationsQuery) -> FetchedRows:
        cache_operation = self._build_cache_operation(query)
        cached_value = await self._cache_worker.try_serve_from_cache(cache_operation)
        if cached_value is not None:
            automations, total = cached_value
            log_served_from_cache(query.user_id)
            return FetchedRows(rows=automations, total=total, cached=True)

        automations, total = await self._make_store_request(query)
        await self._cache_worker.save_to_cache(
            context=cache_operation,
            automations=automations,
            total=total,
        )

        log_served_from_store(query.user_id, automations, total)
        return FetchedRows(rows=automations, total=total, cached=False)

    async def _make_store_request(
        self,
        query: ListAutomationsQuery,
    ) -> tuple[list[AutomationDTO], int]:
        total = await count_owned_automations(
            query.user_id,
            query.filters,
        )
        rows = await fetch_owned_automations(
            query.user_id,
            query.page,
            query.filters,
        )

        return (
            [AutomationDTO.from_read_model(row) for row in rows],
            total,
        )

    def _build_cache_operation(self, query: ListAutomationsQuery) -> CacheOperationData:
        return CacheOperationData(
            user_id=query.user_id,
            filters=query.filters.as_cache_material(),
            limit=query.page.limit,
            cursor=query.page.cache_token,
        )

from redis.asyncio import Redis

from data_read_core.shared.query_results import FetchedRows

from .cache_worker import CacheWorker
from .dtos import ActionDTO, CacheOperationData, ListActionsQuery
from .infra import count_owned_actions, fetch_owned_actions, get_redis_client
from .logger_shortcuts import log_served_from_cache, log_served_from_store


class ListActionsQueryHandler:
    def __init__(self, redis_client: Redis | None = None):
        redis_client = redis_client or get_redis_client()

        self._redis_client = redis_client
        self._cache_worker = CacheWorker(redis_client)

    async def handle(self, query: ListActionsQuery) -> FetchedRows:
        cache_operation = self._build_cache_operation(query)
        cached_value = await self._cache_worker.try_serve_from_cache(cache_operation)
        if cached_value is not None:
            actions, total = cached_value
            log_served_from_cache(query.user_id)
            return FetchedRows(rows=actions, total=total, cached=True)

        actions, total = await self._make_store_request(query)
        await self._cache_worker.save_to_cache(
            context=cache_operation,
            actions=actions,
            total=total,
        )

        log_served_from_store(query.user_id, actions, total)
        return FetchedRows(rows=actions, total=total, cached=False)

    async def _make_store_request(
        self,
        query: ListActionsQuery,
    ) -> tuple[list[ActionDTO], int]:
        total = await count_owned_actions(
            query.user_id,
            query.filters,
        )
        action_rows = await fetch_owned_actions(
            query.user_id,
            query.page,
            query.filters,
        )

        return ([ActionDTO.from_read_model(action) for action in action_rows], total)

    def _build_cache_operation(self, query: ListActionsQuery) -> CacheOperationData:
        return CacheOperationData(
            user_id=query.user_id,
            filters=query.filters.as_cache_material(),
            limit=query.page.limit,
            cursor=query.page.cache_token,
        )

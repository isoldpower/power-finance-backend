from redis.asyncio import Redis

from data_read_core.shared.query_results import FetchedRows

from .cache_worker import CacheWorker
from .dtos import AccountDTO, CacheOperationData, ListAccountsQuery
from .infra import (
    count_owned_accounts,
    fetch_owned_accounts,
    get_redis_client,
)
from .logger_shortcuts import (
    log_served_from_cache,
    log_served_from_store,
)


class ListAccountsQueryHandler:
    def __init__(self, redis_client: Redis | None = None):
        redis_client = redis_client or get_redis_client()

        self._redis_client = redis_client
        self._cache_worker = CacheWorker(redis_client)

    async def handle(self, query: ListAccountsQuery) -> FetchedRows:
        cache_operation = self._build_cache_operation(query)
        cached_value = await self._cache_worker.try_serve_from_cache(cache_operation)
        if cached_value is not None:
            accounts, total = cached_value
            log_served_from_cache(query.user_id)
            return FetchedRows(
                rows=accounts,
                total=total,
                cached=True,
            )

        accounts, total = await self._make_store_request(query)
        await self._cache_worker.save_to_cache(
            context=cache_operation,
            accounts=accounts,
            total=total,
        )

        log_served_from_store(query.user_id, accounts, total)
        return FetchedRows(
            rows=accounts,
            total=total,
            cached=False,
        )

    async def _make_store_request(self, query: ListAccountsQuery) -> tuple[list[AccountDTO], int]:
        total = await count_owned_accounts(query.user_id)
        rows = await fetch_owned_accounts(query.user_id, query.page)

        return ([AccountDTO.from_read_model(row) for row in rows], total)

    def _build_cache_operation(self, query: ListAccountsQuery) -> CacheOperationData:
        return CacheOperationData(
            user_id=query.user_id,
            filters=query.filters,
            limit=query.page.limit,
            cursor=query.page.cache_token,
        )

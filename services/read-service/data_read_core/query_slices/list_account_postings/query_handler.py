from redis.asyncio import Redis

from data_read_core.shared.query_results import FetchedRows

from .cache_worker import CacheWorker
from .dtos import AccountPostingDTO, CacheOperationData, ListAccountPostingsQuery
from .exceptions import AccountNotFoundError
from .infra import (
    account_is_owned,
    count_account_postings,
    fetch_account_postings,
    get_redis_client,
)
from .logger_shortcuts import (
    log_served_from_cache,
    log_served_from_store,
)


class ListAccountPostingsQueryHandler:
    def __init__(self, redis_client: Redis | None = None):
        redis_client = redis_client or get_redis_client()

        self._redis_client = redis_client
        self._cache_worker = CacheWorker(redis_client)

    async def handle(self, query: ListAccountPostingsQuery) -> FetchedRows:
        if not await account_is_owned(query.user_id, query.account_id):
            raise AccountNotFoundError()

        cache_operation = self._build_cache_operation(query)
        cached_value = await self._cache_worker.try_serve_from_cache(cache_operation)
        if cached_value is not None:
            postings, total = cached_value
            log_served_from_cache(query.account_id)
            return FetchedRows(rows=postings, total=total, cached=True)

        postings, total = await self._make_store_request(query)
        await self._cache_worker.save_to_cache(
            context=cache_operation,
            postings=postings,
            total=total,
        )

        log_served_from_store(query.account_id, postings, total)
        return FetchedRows(rows=postings, total=total, cached=False)

    async def _make_store_request(
        self,
        query: ListAccountPostingsQuery,
    ) -> tuple[list[AccountPostingDTO], int]:
        total = await count_account_postings(query.account_id)
        rows = await fetch_account_postings(query.account_id, query.page)

        return [AccountPostingDTO.from_read_model(row) for row in rows], total

    def _build_cache_operation(self, query: ListAccountPostingsQuery) -> CacheOperationData:
        return CacheOperationData(
            account_id=query.account_id,
            filters=query.filters,
            limit=query.page.limit,
            cursor=query.page.cache_token,
        )

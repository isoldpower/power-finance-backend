from redis.asyncio import Redis

from .cache_worker import CacheWorker
from .dtos import (
    CacheOperationData,
    ListTransactionsQuery,
    TransactionDTO,
)
from .infra import (
    count_user_transactions,
    fetch_user_transactions,
    get_redis_client,
)
from .logger_shortcuts import (
    log_served_from_cache,
    log_served_from_store,
)


class ListTransactionsQueryHandler:
    def __init__(self, redis_client: Redis | None = None):
        redis_client = redis_client or get_redis_client()

        self._redis_client = redis_client
        self._cache_worker = CacheWorker(redis_client)

    async def handle(self, query: ListTransactionsQuery) -> tuple[list[TransactionDTO], int]:
        cache_operation = self._build_cache_operation(query)
        cached_value = await self._cache_worker.try_serve_from_cache(cache_operation)
        if cached_value is not None:
            log_served_from_cache(query.user_id)
            return cached_value

        transactions, total = await self._make_store_request(query)
        await self._cache_worker.save_to_cache(
            context=cache_operation,
            transactions=transactions,
            total=total,
        )

        log_served_from_store(query.user_id, transactions, total)
        return transactions, total

    async def _make_store_request(
        self, query: ListTransactionsQuery
    ) -> tuple[list[TransactionDTO], int]:
        total = await count_user_transactions(query.user_id)
        database_entry = await fetch_user_transactions(query.user_id, query.limit, query.offset)
        transactions = [TransactionDTO.from_read_model(entry) for entry in database_entry]

        return transactions, total

    def _build_cache_operation(self, query: ListTransactionsQuery) -> CacheOperationData:
        return CacheOperationData(
            user_id=query.user_id,
            filters=query.filters,
            limit=query.limit,
            offset=query.offset,
        )

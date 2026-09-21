from redis.asyncio import Redis

from data_read_core.shared.query_results import FetchedRows

from .cache_worker import CacheWorker
from .dtos import (
    CacheOperationData,
    ListWalletsQuery,
    WalletDTO,
)
from .infra import (
    count_owned_wallets,
    fetch_owned_wallets,
    get_redis_client,
)
from .logger_shortcuts import (
    log_served_from_cache,
    log_served_from_store,
)


class ListWalletsQueryHandler:
    def __init__(self, redis_client: Redis | None = None):
        redis_client = redis_client or get_redis_client()

        self._redis_client = redis_client
        self._cache_worker = CacheWorker(redis_client)

    async def handle(self, query: ListWalletsQuery) -> FetchedRows:
        cache_operation = self._build_cache_operation(query)
        cached_value = await self._cache_worker.try_serve_from_cache(cache_operation)
        if cached_value is not None:
            wallets, total = cached_value
            log_served_from_cache(query.user_id)
            return FetchedRows(
                rows=wallets,
                total=total,
                cached=True,
            )

        wallets, total = await self._make_store_request(query)
        await self._cache_worker.save_to_cache(
            context=cache_operation,
            wallets=wallets,
            total=total,
        )

        log_served_from_store(
            query.user_id,
            wallets,
            total,
        )
        return FetchedRows(
            rows=wallets,
            total=total,
            cached=False,
        )

    async def _make_store_request(self, query: ListWalletsQuery) -> tuple[list[WalletDTO], int]:
        total = await count_owned_wallets(query.user_id)
        database_entry = await fetch_owned_wallets(query.user_id, query.page)
        wallets = [WalletDTO.from_read_model(entry) for entry in database_entry]

        return wallets, total

    def _build_cache_operation(self, query: ListWalletsQuery) -> CacheOperationData:
        return CacheOperationData(
            user_id=query.user_id,
            filters=query.filters,
            limit=query.page.limit,
            cursor=query.page.cache_token,
        )

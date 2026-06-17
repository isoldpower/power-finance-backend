from redis.asyncio import Redis

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

    async def handle(self, query: ListWalletsQuery) -> tuple[list[WalletDTO], int]:
        cache_operation = self._build_cache_operation(query)
        cached_value = await self._cache_worker.try_serve_from_cache(cache_operation)
        if cached_value is not None:
            log_served_from_cache(query.user_id)
            return cached_value

        wallets, total = await self._make_store_request(query)
        await self._cache_worker.save_to_cache(
            context=cache_operation,
            wallets=wallets,
            total=total,
        )

        log_served_from_store(query.user_id, wallets, total)
        return wallets, total

    async def _make_store_request(self, query: ListWalletsQuery) -> tuple[list[WalletDTO], int]:
        total = await count_owned_wallets(query.user_id)
        database_entry = await fetch_owned_wallets(query.user_id, query.limit, query.offset)
        wallets = [WalletDTO.from_read_model(entry) for entry in database_entry]

        return wallets, total

    def _build_cache_operation(self, query: ListWalletsQuery) -> CacheOperationData:
        return CacheOperationData(
            user_id=query.user_id,
            filters=query.filters,
            limit=query.limit,
            offset=query.offset,
        )

from redis.asyncio import Redis

from data_read_core.shared.query_results import FetchedResource

from .cache_worker import CacheWorker
from .dtos import GetWalletQuery, WalletDTO
from .exceptions import WalletNotFoundError
from .infra import fetch_owned_wallet, get_redis_client
from .logger_shortcuts import log_served_from_cache, log_served_from_store


class GetWalletQueryHandler:
    def __init__(self, redis_client: Redis | None = None):
        redis_client = redis_client or get_redis_client()

        self._redis_client = redis_client
        self._cache_worker = CacheWorker(redis_client)

    async def handle(self, query: GetWalletQuery) -> FetchedResource:
        cached_value = await self._cache_worker.try_serve_from_cache(
            query.wallet_id,
            query.user_id,
        )
        if cached_value is not None:
            log_served_from_cache(query.wallet_id)
            return FetchedResource(
                resource=cached_value,
                cached=True,
            )

        owned_wallet = await fetch_owned_wallet(query.user_id, query.wallet_id)
        if owned_wallet is None:
            raise WalletNotFoundError()

        wallet = WalletDTO.from_read_model(owned_wallet)
        await self._cache_worker.save_to_cache(wallet)

        log_served_from_store(query.wallet_id)
        return FetchedResource(
            resource=wallet,
            cached=False,
        )

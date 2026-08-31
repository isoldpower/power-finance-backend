from redis.asyncio import Redis

from data_read_core.shared.query_results import FetchedResource

from .cache_worker import CacheWorker
from .dtos import GetTransactionQuery, TransactionDTO
from .exceptions import TransactionNotFoundError
from .infra import (
    fetch_owned_transaction,
    fetch_transaction_dispatch,
    fetch_transaction_postings,
    get_redis_client,
)
from .logger_shortcuts import log_served_from_cache, log_served_from_store


class GetTransactionQueryHandler:
    def __init__(self, redis_client: Redis | None = None):
        redis_client = redis_client or get_redis_client()

        self._redis_client = redis_client
        self._cache_worker = CacheWorker(redis_client)

    async def handle(self, query: GetTransactionQuery) -> FetchedResource:
        cached_value = await self._cache_worker.try_serve_from_cache(
            query.transaction_id, query.user_id
        )
        if cached_value is not None:
            log_served_from_cache(query.transaction_id)
            return FetchedResource(
                resource=cached_value,
                cached=True,
            )

        model = await fetch_owned_transaction(query.user_id, query.transaction_id)
        if model is None:
            raise TransactionNotFoundError()

        transaction = TransactionDTO.from_read_model(
            model,
            postings=await fetch_transaction_postings(query.transaction_id),
            dispatch=await fetch_transaction_dispatch(query.transaction_id),
        )
        await self._cache_worker.save_to_cache(transaction)

        log_served_from_store(query.transaction_id)
        return FetchedResource(
            resource=transaction,
            cached=False,
        )

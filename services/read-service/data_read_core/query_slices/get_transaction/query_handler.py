from redis.asyncio import Redis

from .cache_worker import CacheWorker
from .dtos import GetTransactionQuery, TransactionDTO
from .exceptions import TransactionNotFoundError
from .infra import fetch_owned_transaction, get_redis_client
from .logger_shortcuts import log_served_from_cache, log_served_from_store


class GetTransactionQueryHandler:
    def __init__(self, redis_client: Redis | None = None):
        redis_client = redis_client or get_redis_client()

        self._redis_client = redis_client
        self._cache_worker = CacheWorker(redis_client)

    async def handle(self, query: GetTransactionQuery) -> TransactionDTO:
        cached_value = await self._cache_worker.try_serve_from_cache(
            query.transaction_id, query.user_id
        )
        if cached_value is not None:
            log_served_from_cache(query.transaction_id)
            return cached_value

        model = await fetch_owned_transaction(query.user_id, query.transaction_id)
        if model is None:
            raise TransactionNotFoundError(
                f"Transaction {query.transaction_id} not found for user {query.user_id}"
            )

        transaction = TransactionDTO.from_read_model(model)
        await self._cache_worker.save_to_cache(transaction)

        log_served_from_store(query.transaction_id)
        return transaction

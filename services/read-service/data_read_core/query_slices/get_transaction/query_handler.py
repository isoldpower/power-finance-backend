import json
from logging import getLogger

from redis.asyncio import Redis

from .dtos import GetTransactionQuery, TransactionDTO
from .exceptions import TransactionNotFoundError
from .infra import (
    fetch_owned_transaction,
    get_redis_client,
    get_single_cache_key,
)

logger = getLogger("query_slices.get_transaction")

CACHE_TTL_SECONDS = 300


class GetTransactionQueryHandler:
    def __init__(
        self,
        redis_client: Redis | None = None,
    ):
        self._redis_client = redis_client or get_redis_client()

    async def handle(self, query: GetTransactionQuery) -> TransactionDTO:
        cached_value = await self._try_retrieve_from_cache(query.transaction_id, query.user_id)
        if cached_value is not None:
            return cached_value

        model = await fetch_owned_transaction(query.user_id, query.transaction_id)
        if model is None:
            raise TransactionNotFoundError(
                f"Transaction {query.transaction_id} not found for user {query.user_id}"
            )

        transaction = TransactionDTO.from_read_model(model)
        await self._save_to_cache(transaction)

        logger.info("Served transaction %s from read store.", query.transaction_id)
        return transaction

    async def _try_retrieve_from_cache(
        self, transaction_id: str, user_id: int
    ) -> TransactionDTO | None:
        cache_key = get_single_cache_key(transaction_id)
        cached_value = await self._redis_client.get(cache_key)

        if cached_value is not None:
            transaction = TransactionDTO.from_cache(json.loads(cached_value))

            if transaction.user_id == user_id:
                logger.info("Served transaction %s from cache.", transaction_id)
                return transaction
            else:
                await self._redis_client.delete(cache_key)

        return None

    async def _save_to_cache(self, transaction: TransactionDTO) -> None:
        cache_key = get_single_cache_key(transaction.id)
        await self._redis_client.set(
            cache_key,
            json.dumps(transaction.to_cache()),
            ex=CACHE_TTL_SECONDS,
        )

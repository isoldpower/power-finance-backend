from kafka_consumer_py import Effect, EventMessage
from kafka_messages import CategoryUpdated

from data_read_core.shared.postgres_orm import TransactionReadModel, WalletReadModel
from data_read_core.shared.redis_cache import get_redis

from .._cache_keys import get_single_transaction_key, get_single_wallet_key
from .._logger_shortcuts import log_categorised_caches_evicted
from .._utilities import decode_payload

EVICTION_BATCH_SIZE = 500


class EvictCategorisedItemCaches(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, CategoryUpdated)
        cache_keys = [
            get_single_wallet_key(str(wallet_id))
            async for wallet_id in WalletReadModel.objects.filter(
                category_id=payload.category_id
            ).values_list("id", flat=True)
        ]
        cache_keys.extend(
            [
                get_single_transaction_key(str(transaction_id))
                async for transaction_id in TransactionReadModel.objects.filter(
                    category_id=payload.category_id
                ).values_list("id", flat=True)
            ]
        )

        redis_client = get_redis()
        for batch_start in range(0, len(cache_keys), EVICTION_BATCH_SIZE):
            await redis_client.delete(*cache_keys[batch_start : batch_start + EVICTION_BATCH_SIZE])

        log_categorised_caches_evicted(payload.category_id, len(cache_keys))

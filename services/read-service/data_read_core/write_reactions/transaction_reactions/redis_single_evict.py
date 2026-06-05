from logging import getLogger

from google.protobuf.message import Message
from kafka_messages import TransactionDeleted

from data_read_core.shared.kafka_updates import Effect, EventMessage
from data_read_core.shared.redis_cache import get_redis

from .._cache_keys import get_single_transaction_key
from .._utilities import decode_payload

logger = getLogger("background_workers.write_message_consumer")


class EvictTransactionCache(Effect):
    def __init__(self, payload_type: type[Message] = TransactionDeleted) -> None:
        self._payload_type = payload_type

    async def apply(self, event: EventMessage) -> None:
        event_payload = decode_payload(event, self._payload_type)
        key = get_single_transaction_key(event_payload.transaction_id)
        removed_resource = await get_redis().delete(key)

        logger.info(
            "Evicted cache key %s (removed=%s).",
            key,
            removed_resource,
        )

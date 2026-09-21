from google.protobuf.message import Message
from kafka_consumer_py import Effect, EventMessage
from kafka_messages import AccountUpdated

from data_read_core.shared.redis_cache import get_redis

from .._cache_keys import get_single_account_key
from .._logger_shortcuts import log_account_cache_evicted
from .._utilities import decode_payload


class EvictAccountCache(Effect):
    def __init__(self, payload_type: type[Message] = AccountUpdated) -> None:
        self._payload_type = payload_type

    async def apply(self, event: EventMessage) -> None:
        event_payload = decode_payload(event, self._payload_type)
        key = get_single_account_key(event_payload.account_id)
        removed_resource = await get_redis().delete(key)

        log_account_cache_evicted(key, removed_resource)

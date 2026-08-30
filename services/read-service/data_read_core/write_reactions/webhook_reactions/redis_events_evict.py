from google.protobuf.message import Message
from kafka_consumer_py import Effect, EventMessage

from data_read_core.shared.redis_cache import get_redis

from .._cache_keys import get_webhook_events_key
from .._logger_shortcuts import log_webhook_cache_evicted
from .._utilities import decode_payload


class EvictWebhookEventsCache(Effect):
    """Evict the cached subscription list for a webhook, keyed by webhook id."""

    def __init__(self, payload_type: type[Message]) -> None:
        self._payload_type = payload_type

    async def apply(self, event: EventMessage) -> None:
        event_payload = decode_payload(event, self._payload_type)
        key = get_webhook_events_key(event_payload.webhook_id)
        removed_resource = await get_redis().delete(key)

        log_webhook_cache_evicted(key, removed_resource)

from google.protobuf.message import Message
from kafka_consumer_py import Effect, EventMessage
from kafka_messages import NotificationDeleted, NotificationsAcknowledged

from data_read_core.shared.redis_cache import get_redis

from .._cache_keys import get_single_notification_key
from .._logger_shortcuts import log_notification_cache_evicted
from .._utilities import decode_payload


class EvictNotificationCache(Effect):
    """Evict the single-notification cache entry keyed by notification id."""

    def __init__(self, payload_type: type[Message] = NotificationDeleted) -> None:
        self._payload_type = payload_type

    async def apply(self, event: EventMessage) -> None:
        event_payload = decode_payload(event, self._payload_type)
        key = get_single_notification_key(event_payload.notification_id)
        removed_resource = await get_redis().delete(key)

        log_notification_cache_evicted(key, removed_resource)


class EvictAcknowledgedNotificationsCache(Effect):
    """Evict the single-notification cache entry of every acknowledged id."""

    async def apply(self, event: EventMessage) -> None:
        event_payload = decode_payload(event, NotificationsAcknowledged)
        for notification_id in event_payload.notification_ids:
            key = get_single_notification_key(notification_id)
            removed_resource = await get_redis().delete(key)

            log_notification_cache_evicted(key, removed_resource)

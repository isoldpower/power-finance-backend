from google.protobuf.message import Message
from kafka_consumer_py import EventMessage
from kafka_consumer_py.processing import Effect
from kafka_messages import GoalDeleted

from data_read_core.shared.redis_cache import get_redis

from .._cache_keys import get_single_goal_key
from .._logger_shortcuts import log_goal_cache_evicted
from .._utilities import decode_payload


class EvictGoalCache(Effect):
    """Evict the single-goal cache entry keyed by goal id."""

    def __init__(self, payload_type: type[Message] = GoalDeleted) -> None:
        self._payload_type = payload_type

    async def apply(self, event: EventMessage) -> None:
        event_payload = decode_payload(event, self._payload_type)
        key = get_single_goal_key(event_payload.goal_id)
        removed_resource = await get_redis().delete(key)

        log_goal_cache_evicted(key, removed_resource)

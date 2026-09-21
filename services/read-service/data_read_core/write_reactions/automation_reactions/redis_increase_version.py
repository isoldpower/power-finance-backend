from google.protobuf.message import Message
from kafka_consumer_py import Effect, EventMessage

from data_read_core.shared.redis_cache import get_redis

from .._cache_keys import get_automation_list_version_key
from .._logger_shortcuts import log_automation_list_version_bumped
from .._utilities import decode_payload


class BumpAutomationListVersion(Effect):
    def __init__(self, payload_type: type[Message]) -> None:
        self._payload_type = payload_type

    async def apply(self, event: EventMessage) -> None:
        event_payload = decode_payload(event, self._payload_type)
        version_key = get_automation_list_version_key(event_payload.user_id)
        new_version = await get_redis().incr(version_key)

        log_automation_list_version_bumped(
            event_payload.user_id,
            new_version,
        )

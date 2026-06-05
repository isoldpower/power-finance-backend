from logging import getLogger

from google.protobuf.message import Message

from data_read_core.shared.kafka_updates import Effect, EventMessage
from data_read_core.shared.redis_cache import get_redis

from .._cache_keys import get_transaction_list_version_key
from .._utilities import decode_payload

logger = getLogger("background_workers.write_message_consumer")


class BumpTransactionListVersion(Effect):
    """Invalidate every cached transaction-list page for the user by bumping the
    per-user list version counter."""

    def __init__(self, payload_type: type[Message]) -> None:
        self._payload_type = payload_type

    async def apply(self, event: EventMessage) -> None:
        event_payload = decode_payload(event, self._payload_type)
        key = get_transaction_list_version_key(event_payload.user_id)
        new_version = await get_redis().incr(key)

        logger.info(
            "Bumped transaction list version for user %s to %s.",
            event_payload.user_id,
            new_version,
        )

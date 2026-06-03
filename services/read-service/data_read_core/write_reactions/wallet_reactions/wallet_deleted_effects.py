from logging import getLogger

from google.protobuf.message import Message
from kafka_messages import WalletDeleted

from data_read_core.shared.kafka_updates import EventMessage
from data_read_core.shared.kafka_updates.processing import Effect
from data_read_core.shared.postgres_orm import WalletReadModel
from data_read_core.shared.redis_cache import get_redis

from .._cache_keys import get_single_wallet_key
from .._utilities import decode_payload, handle_database_errors

logger = getLogger("background_workers.write_message_consumer")


class RemoveWalletReadModel(Effect):
    """Delete the wallet projection row from the read store."""

    async def apply(self, event: EventMessage) -> None:
        event_payload = decode_payload(event, WalletDeleted)
        await handle_database_errors(
            _remove_wallet,
            event_payload,
            resource_id=event_payload.wallet_id,
        )


async def _remove_wallet(payload: WalletDeleted) -> None:
    deleted, _ = await WalletReadModel.objects.filter(id=payload.wallet_id).adelete()
    logger.info(
        "Removed wallet %s from read store (rows=%s).",
        payload.wallet_id,
        deleted,
    )


class EvictWalletCache(Effect):
    """Evict the single-wallet cache entry keyed by wallet id."""

    def __init__(self, payload_type: type[Message] = WalletDeleted) -> None:
        self._payload_type = payload_type

    async def apply(self, event: EventMessage) -> None:
        event_payload = decode_payload(event, self._payload_type)
        key = get_single_wallet_key(event_payload.wallet_id)
        removed_resource = await get_redis().delete(key)

        logger.info(
            "Evicted cache key %s (removed=%s).",
            key,
            removed_resource,
        )

from logging import getLogger

from google.protobuf.message import Message

from data_read_core.shared.kafka_updates import Effect, EventMessage
from data_read_core.shared.postgres_orm import aatomic
from data_read_core.shared.read_at_least import record_applied_seq

from ._utilities import decode_payload

logger = getLogger("background_workers.write_message_consumer")


class TrackAppliedSeq(Effect):
    """Wrap a projection Effect so the originating outbox seq is recorded in the
    same transaction as the projection write."""

    def __init__(self, inner: Effect, payload_type: type[Message]) -> None:
        self._inner = inner
        self._payload_type = payload_type

    @property
    def name(self) -> str:
        return f"TrackAppliedSeq({self._inner.name})"

    async def apply(self, event: EventMessage) -> None:
        if event.outbox_seq is None:
            logger.warning(
                "Event %s carries no outbox seq; projecting without advancing "
                "read-your-writes progress.",
                event.event_id,
            )

            await self._inner.apply(event)
            return

        decoded_payload = decode_payload(event, self._payload_type)
        async with aatomic():
            await self._inner.apply(event)
            await record_applied_seq(
                decoded_payload.user_id,
                event.outbox_seq,
            )

    async def compensate(self, event: EventMessage) -> None:
        await self._inner.compensate(event)

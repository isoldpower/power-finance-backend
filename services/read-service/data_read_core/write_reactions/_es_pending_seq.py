from google.protobuf.message import Message
from kafka_consumer_py import EventMessage, Handler

from data_read_core.shared.read_at_least import clear_es_pending_seq, record_es_pending_seq

from ._logger_shortcuts import warn_no_outbox_sequence
from ._utilities import decode_payload


class TrackEsPendingSeq:
    """Holds the search Read-At-Least watermark below an event whose plan failed.

    Wraps the whole search plan rather than one effect, so a failure in any step
    (not only the one recording `applied_seq`) leaves the hold in place until a
    retry or a DLQ replay of the same event succeeds.
    """

    def __init__(self, handler: Handler, payload_type: type[Message]) -> None:
        self._handler = handler
        self._payload_type = payload_type

    async def __call__(self, event: EventMessage) -> None:
        if event.outbox_seq is None:
            warn_no_outbox_sequence(event.event_id)
            await self._handler(event)
            return

        user_id = decode_payload(event, self._payload_type).user_id
        try:
            await self._handler(event)
        except Exception:
            await record_es_pending_seq(user_id, event.outbox_seq, event.event_id)
            raise

        await clear_es_pending_seq(user_id, event.outbox_seq)

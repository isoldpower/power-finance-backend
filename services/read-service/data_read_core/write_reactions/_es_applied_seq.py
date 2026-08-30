from google.protobuf.message import Message
from kafka_consumer_py import Effect, EventMessage

from data_read_core.shared.read_at_least import record_es_applied_seq

from ._logger_shortcuts import warn_no_outbox_sequence
from ._utilities import decode_payload


class TrackEsAppliedSeq(Effect):
    """Wrap an Elasticsearch projection Effect so the originating outbox seq is
    recorded in the ES applied-seq table after the document write succeeds."""

    def __init__(self, inner: Effect, payload_type: type[Message]) -> None:
        self._inner = inner
        self._payload_type = payload_type

    @property
    def name(self) -> str:
        return f"TrackEsAppliedSeq({self._inner.name})"

    async def apply(self, event: EventMessage) -> None:
        await self._inner.apply(event)

        if event.outbox_seq is None:
            warn_no_outbox_sequence(event.event_id)
            return

        decoded_payload = decode_payload(event, self._payload_type)
        await record_es_applied_seq(decoded_payload.user_id, event.outbox_seq)

    async def compensate(self, event: EventMessage) -> None:
        await self._inner.compensate(event)

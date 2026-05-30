from kafka_client_py import (
    ConsumedMessage,
)
from kafka_client_py import (
    envelope as KafkaEnvelope,
)
from kafka_client_py import (
    headers as KafkaHeaders,
)

from ..exceptions import MalformedEnvelope
from ..types import EventMessage


class OutboxEnvelopeDecoder:
    def decode(self, message: ConsumedMessage) -> EventMessage:
        event_id = self.extract_event_id(message)
        event_type = self.extract_event_type(message)
        if not event_id or not event_type:
            raise MalformedEnvelope(
                f"missing required headers: event_id={bool(event_id)} "
                f"event_type={bool(event_type)}"
            )

        return EventMessage(
            event_id=event_id,
            event_type=event_type,
            aggregate_type=self._extract_aggregate_type(message),
            aggregate_id=self._extract_aggregate_id(message),
            outbox_seq=self._extract_outbox_sequence(message),
            payload=self._extract_value_safe(message),
            headers=self._copy_headers_safe(message),
            topic=self._extract_topic(message),
            partition=self._extract_partition(message),
            offset=self._extract_offset(message),
        )

    def extract_event_id(self, message: ConsumedMessage) -> str | None:
        return KafkaHeaders.get(message.headers, KafkaEnvelope.HEADER_EVENT_ID)

    def extract_event_type(self, message: ConsumedMessage) -> str | None:
        return KafkaHeaders.get(message.headers, KafkaEnvelope.HEADER_EVENT_TYPE)

    def _extract_aggregate_type(self, message: ConsumedMessage) -> str:
        return KafkaHeaders.get(message.headers, KafkaEnvelope.HEADER_AGGREGATE_TYPE) or ""

    def _extract_aggregate_id(self, message: ConsumedMessage) -> str:
        return message.key.decode("utf-8") if message.key else ""

    def _extract_outbox_sequence(self, message: ConsumedMessage) -> int | None:
        outbox_seq_raw = KafkaHeaders.get(message.headers, KafkaEnvelope.HEADER_OUTBOX_SEQ)
        return int(outbox_seq_raw) if outbox_seq_raw else None

    def _extract_value_safe(self, message: ConsumedMessage) -> bytes:
        return message.value or b""

    def _copy_headers_safe(self, message: ConsumedMessage) -> dict:
        return {name: value for name, value in (message.headers or [])}

    def _extract_topic(self, message: ConsumedMessage) -> str:
        return message.topic

    def _extract_partition(self, message: ConsumedMessage) -> int:
        return message.partition

    def _extract_offset(self, message: ConsumedMessage) -> int:
        return message.offset

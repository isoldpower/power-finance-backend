import logging

from kafka_client_py import ConsumedMessage
from kafka_client_py.publisher.dlq_publisher import DLQPublisher

from ..exceptions import MalformedEnvelope
from ..types import EnvelopeDecoder, EventRouter

logger = logging.getLogger(__name__)


class RoutedMessageProcessor:
    def __init__(
        self,
        decoder: EnvelopeDecoder,
        router: EventRouter,
        malformed_dlq: DLQPublisher,
    ) -> None:
        self._decoder = decoder
        self._router = router
        self._malformed_dlq = malformed_dlq

    async def __call__(self, message: ConsumedMessage) -> None:
        try:
            event = self._decoder.decode(message)
        except MalformedEnvelope as decode_error:
            await self._malformed_dlq.publish(
                message,
                error=decode_error,
                total_attempts=1,
            )
            logger.warning(
                "malformed envelope routed to DLQ; topic=%s partition=%s offset=%s",
                message.topic,
                message.partition,
                message.offset,
            )
            return

        if not self._router.has(event.event_type):
            logger.debug(
                "no handler registered; event_type=%s offset=%s — skipping",
                event.event_type,
                message.offset,
            )
            return

        await self._router.dispatch(event)

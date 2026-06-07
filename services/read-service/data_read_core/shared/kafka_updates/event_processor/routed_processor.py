from kafka_client_py import ConsumedMessage
from kafka_client_py.publisher.dlq_publisher import DLQPublisher

from ..exceptions import MalformedEnvelope
from ..logger_shortcuts import debug_no_event_handler, warn_routed_to_dlq
from ..types import EnvelopeDecoder, EventRouter


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
            warn_routed_to_dlq(message)
            return

        if not self._router.has(event.event_type):
            debug_no_event_handler(event.event_type, message)
            return

        await self._router.dispatch(event)

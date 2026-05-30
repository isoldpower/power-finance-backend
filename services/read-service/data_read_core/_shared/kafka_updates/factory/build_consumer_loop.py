from kafka_client_py import (
    DedupeStore,
    DLQPublisher,
    MessageHandler,
    RetryPolicy,
    RetryPublisher,
)

from ..event_processor import OutboxEnvelopeDecoder, RoutedMessageProcessor
from ..kafka_consumer import KafkaConsumerLoop
from ..shutdown_signals import SigtermShutdownSignal
from ..types import (
    ConsumerLoop,
    EnvelopeDecoder,
    EventRouter,
    ShutdownSignal,
)
from .build_consumer import build_aiokafka_consumer
from .types import ConsumerConfig


def build_consumer_loop(
    *,
    config: ConsumerConfig,
    router: EventRouter,
    retry_policy: RetryPolicy,
    retry_publisher: RetryPublisher,
    dlq_publisher: DLQPublisher,
    dedupe_store: DedupeStore | None = None,
    decoder: EnvelopeDecoder | None = None,
    shutdown: ShutdownSignal | None = None,
    install_signal_handlers: bool = True,
) -> ConsumerLoop:
    """Wires every collaborator a ConsumerLoop needs"""

    actual_decoder = decoder or OutboxEnvelopeDecoder()
    actual_shutdown = shutdown or SigtermShutdownSignal()

    if install_signal_handlers and isinstance(actual_shutdown, ShutdownSignal):
        actual_shutdown.install()

    processor = RoutedMessageProcessor(
        decoder=actual_decoder,
        router=router,
        malformed_dlq=dlq_publisher,
    )
    message_handler = MessageHandler(
        user_handler=processor,
        policy=retry_policy,
        retry_publisher=retry_publisher,
        dlq_publisher=dlq_publisher,
        dedupe=dedupe_store,
        event_id=actual_decoder.extract_event_id,
    )

    return KafkaConsumerLoop(
        consumer=build_aiokafka_consumer(config),
        message_handler=message_handler,
        shutdown=actual_shutdown,
        poll_timeout_ms=config.poll_timeout_ms,
    )

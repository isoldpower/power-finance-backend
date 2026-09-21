from kafka_client_py import (
    DedupeStore,
    DLQPublisher,
    MessageHandler,
    RetryPolicy,
    RetryPublisher,
)

from ..event_processor import (
    ContextBoundMessageProcessor,
    OutboxEnvelopeDecoder,
    RoutedMessageProcessor,
    SandboxFilteredMessageProcessor,
)
from ..kafka_consumer import KafkaConsumerLoop
from ..message_context import (
    MessageContextBinder,
    NullMessageContextBinder,
    PermissiveSandboxTrafficPolicy,
    SandboxTrafficPolicy,
)
from ..shutdown_signals import SigtermShutdownSignal
from ..types import (
    ConsumerLoop,
    EnvelopeDecoder,
    EventRouter,
    MessageProcessor,
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
    dedupe_store: DedupeStore | None,
    decoder: EnvelopeDecoder | None = None,
    shutdown: ShutdownSignal | None = None,
    context_binder: MessageContextBinder | None = None,
    traffic_policy: SandboxTrafficPolicy | None = None,
    install_signal_handlers: bool = True,
) -> ConsumerLoop:
    """Wires every collaborator a ConsumerLoop needs"""

    actual_decoder = decoder or OutboxEnvelopeDecoder()
    actual_shutdown = shutdown or SigtermShutdownSignal()

    if install_signal_handlers and isinstance(actual_shutdown, ShutdownSignal):
        actual_shutdown.install()

    actual_context_binder = context_binder or NullMessageContextBinder()
    actual_traffic_policy = traffic_policy or PermissiveSandboxTrafficPolicy()

    processor = _wrap_with_message_context(
        RoutedMessageProcessor(
            decoder=actual_decoder,
            router=router,
            malformed_dlq=dlq_publisher,
        ),
        context_binder=actual_context_binder,
        traffic_policy=actual_traffic_policy,
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


def _wrap_with_message_context(
    routed_processor: MessageProcessor,
    *,
    context_binder: MessageContextBinder,
    traffic_policy: SandboxTrafficPolicy,
) -> MessageProcessor:
    return ContextBoundMessageProcessor(
        SandboxFilteredMessageProcessor(
            routed_processor,
            context_binder=context_binder,
            traffic_policy=traffic_policy,
        ),
        context_binder=context_binder,
    )

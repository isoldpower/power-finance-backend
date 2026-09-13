import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence

from aiokafka import AIOKafkaConsumer
from kafka_client_py import (
    AsyncPublisher,
    ConsumedMessage,
    DLQPublisher,
    MessageHandler,
    ProducerConfig,
    RetryPolicy,
    RetryPublisher,
)

from .event_processor import ContextBoundMessageProcessor, SandboxFilteredMessageProcessor
from .factory import ConsumerConfig, build_aiokafka_consumer
from .message_context import (
    MessageContextBinder,
    NullMessageContextBinder,
    PermissiveSandboxTrafficPolicy,
    SandboxTrafficPolicy,
)

MessageCallback = Callable[[ConsumedMessage], Awaitable[None]]
AsyncCloser = Callable[[], Awaitable[None]]


class KafkaConsumerRunner:
    """Drives a transactional Kafka consume loop."""

    def __init__(
        self,
        config: ConsumerConfig,
        handler: MessageCallback,
        *,
        logger: logging.Logger,
        name: str,
        closers: Sequence[AsyncCloser] = (),
        context_binder: MessageContextBinder | None = None,
        traffic_policy: SandboxTrafficPolicy | None = None,
    ) -> None:
        self._config = config
        self._handler = handler
        self._logger = logger
        self._name = name
        self._closers = closers
        self._context_binder = context_binder or NullMessageContextBinder()
        self._traffic_policy = traffic_policy or PermissiveSandboxTrafficPolicy()

    def _build_consumer(self) -> AIOKafkaConsumer:
        return build_aiokafka_consumer(self._config)

    def _build_message_processor(self) -> MessageCallback:
        return ContextBoundMessageProcessor(
            SandboxFilteredMessageProcessor(
                self._handler,
                self._context_binder,
                self._traffic_policy,
            ),
            self._context_binder,
        )

    def _build_publisher(self) -> AsyncPublisher:
        return AsyncPublisher(ProducerConfig(bootstrap_servers=self._config.bootstrap_servers))

    async def run(self) -> None:
        config = self._config
        consumer = self._build_consumer()
        publisher = self._build_publisher()

        await asyncio.gather(publisher.start(), consumer.start())
        message_handler = MessageHandler(
            self._build_message_processor(),
            policy=RetryPolicy(),
            retry_publisher=RetryPublisher(publisher),
            dlq_publisher=DLQPublisher(publisher),
        )

        self._logger.info(
            "%s: consumer started (group=%s topics=%s)",
            self._name,
            config.group_id,
            list(config.topics),
        )
        try:
            async for record in consumer:
                await message_handler.handle(record)
                await consumer.commit()
        finally:
            await asyncio.gather(
                consumer.stop(),
                publisher.stop(),
                *(closer() for closer in self._closers),
            )
            self._logger.info("%s: consumer stopped", self._name)

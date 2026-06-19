import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass

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

MessageCallback = Callable[[ConsumedMessage], Awaitable[None]]
AsyncCloser = Callable[[], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class ConsumerConfig:
    """Connection settings shared by every transactional Kafka consumer."""

    bootstrap_servers: str
    group_id: str
    topics: Sequence[str]
    auto_offset_reset: str = "earliest"


class KafkaConsumerRunner:
    """Drives a transactional Kafka consume loop.

    Starts the consumer and producer, dispatches each record through
    retry/DLQ-aware handling, commits per record, and tears everything
    down on shutdown — including any extra resources passed as ``closers``.
    """

    def __init__(
        self,
        config: ConsumerConfig,
        handler: MessageCallback,
        *,
        logger: logging.Logger,
        name: str,
        closers: Sequence[AsyncCloser] = (),
    ) -> None:
        self._config = config
        self._handler = handler
        self._logger = logger
        self._name = name
        self._closers = closers

    def _build_consumer(self) -> AIOKafkaConsumer:
        config = self._config
        return AIOKafkaConsumer(
            *config.topics,
            bootstrap_servers=config.bootstrap_servers,
            group_id=config.group_id,
            enable_auto_commit=False,
            auto_offset_reset=config.auto_offset_reset,
            isolation_level="read_committed",
        )

    def _build_publisher(self) -> AsyncPublisher:
        return AsyncPublisher(ProducerConfig(bootstrap_servers=self._config.bootstrap_servers))

    async def run(self) -> None:
        config = self._config
        consumer = self._build_consumer()
        publisher = self._build_publisher()

        await asyncio.gather(publisher.start(), consumer.start())

        message_handler = MessageHandler(
            self._handler,
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

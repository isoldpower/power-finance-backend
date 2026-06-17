import asyncio
import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass

from aiokafka import AIOKafkaConsumer
from data_write_core.application.commands import (
    CreateNotificationCommand,
    CreateNotificationCommandHandler,
)
from kafka_client_py import (
    AsyncPublisher,
    ConsumedMessage,
    DLQPublisher,
    MessageHandler,
    PoisonError,
    ProducerConfig,
    RetryPolicy,
    RetryPublisher,
)

logger = logging.getLogger("background_workers.inbound_notifications")


@dataclass(frozen=True, slots=True)
class InboundConsumerConfig:
    bootstrap_servers: str
    group_id: str
    topics: Sequence[str]
    auto_offset_reset: str = "earliest"


async def handle_notification_request(message: ConsumedMessage) -> None:
    command = _parse_notification_request(message)
    await CreateNotificationCommandHandler().handle(command)
    logger.info(
        "inbound_notifications: created notification for user_id=%s (short=%r)",
        command.user_id,
        command.short,
    )


def _parse_notification_request(message: ConsumedMessage) -> CreateNotificationCommand:
    if message.value is None:
        raise PoisonError("Empty message on the inbound notifications topic")

    try:
        request = json.loads(message.value)
        return CreateNotificationCommand(
            user_id=int(request["user_id"]),
            user_external_id=str(request["user_external_id"]),
            short=str(request["short"]),
            message=str(request["message"]),
            payload=request.get("payload") or None,
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise PoisonError(f"Malformed NotificationRequested message: {exc}") from exc


async def run_inbound_notifications_consumer(config: InboundConsumerConfig) -> None:
    consumer = AIOKafkaConsumer(
        *config.topics,
        bootstrap_servers=config.bootstrap_servers,
        group_id=config.group_id,
        enable_auto_commit=False,
        auto_offset_reset=config.auto_offset_reset,
        isolation_level="read_committed",
    )
    publisher = AsyncPublisher(
        ProducerConfig(
            bootstrap_servers=config.bootstrap_servers,
        )
    )

    await asyncio.gather(
        *[
            publisher.start(),
            consumer.start(),
        ]
    )
    message_handler = MessageHandler(
        handle_notification_request,
        policy=RetryPolicy(),
        retry_publisher=RetryPublisher(publisher),
        dlq_publisher=DLQPublisher(publisher),
    )

    logger.info(
        "inbound_notifications: consumer started (group=%s topics=%s)",
        config.group_id,
        list(config.topics),
    )
    try:
        async for record in consumer:
            await message_handler.handle(record)
            await consumer.commit()
    finally:
        await asyncio.gather(
            *[
                consumer.stop(),
                publisher.stop(),
            ]
        )

        logger.info("inbound_notifications: consumer stopped")

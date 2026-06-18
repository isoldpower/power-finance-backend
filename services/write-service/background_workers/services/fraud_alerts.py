import asyncio
import logging
from collections.abc import Awaitable, Sequence
from dataclasses import dataclass
from typing import cast

from aiokafka import AIOKafkaConsumer
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
from redis.asyncio import Redis

logger = logging.getLogger("background_workers.fraud_alerts")


@dataclass(frozen=True, slots=True)
class FraudAlertsConsumerConfig:
    bootstrap_servers: str
    group_id: str
    topics: Sequence[str]
    redis_host: str
    redis_port: int
    redis_password: str
    redis_db: int
    auto_offset_reset: str = "earliest"


@dataclass(frozen=True, slots=True)
class SuspendedUser:
    clerk_id: str
    reason: str


class SuspendedUserStore:
    """Records users suspended for fraud in a Redis hash keyed by Clerk id."""

    SUSPENDED_USERS_KEY = "fraud:suspended"

    def __init__(self, client: Redis) -> None:
        self._client = client

    async def suspend(self, user: SuspendedUser) -> None:
        # redis-py types hset as `int | Awaitable[int]`; on the async client it
        # is always awaitable.
        await cast(
            Awaitable[int],
            self._client.hset(self.SUSPENDED_USERS_KEY, user.clerk_id, user.reason),
        )

    async def close(self) -> None:
        await self._client.aclose()


def _parse_fraud_alert(message: ConsumedMessage) -> SuspendedUser:
    if message.key is None:
        raise PoisonError("Fraud alert missing key (clerk id)")

    clerk_id = message.key.decode("utf-8")
    if not clerk_id:
        raise PoisonError("Fraud alert has an empty clerk id")

    reason = message.value.decode("utf-8") if message.value is not None else ""
    return SuspendedUser(clerk_id=clerk_id, reason=reason)


async def handle_fraud_alert(message: ConsumedMessage, store: SuspendedUserStore) -> None:
    user = _parse_fraud_alert(message)
    await store.suspend(user)
    logger.info("fraud_alerts: suspended user clerk_id=%s", user.clerk_id)


async def run_fraud_alerts_consumer(config: FraudAlertsConsumerConfig) -> None:
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
    store = SuspendedUserStore(
        Redis(
            host=config.redis_host,
            port=config.redis_port,
            password=config.redis_password or None,
            db=config.redis_db,
            decode_responses=False,
        )
    )

    await asyncio.gather(
        *[
            publisher.start(),
            consumer.start(),
        ]
    )

    async def handler(message: ConsumedMessage) -> None:
        await handle_fraud_alert(message, store)

    message_handler = MessageHandler(
        handler,
        policy=RetryPolicy(),
        retry_publisher=RetryPublisher(publisher),
        dlq_publisher=DLQPublisher(publisher),
    )

    logger.info(
        "fraud_alerts: consumer started (group=%s topics=%s)",
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
                store.close(),
            ]
        )

        logger.info("fraud_alerts: consumer stopped")

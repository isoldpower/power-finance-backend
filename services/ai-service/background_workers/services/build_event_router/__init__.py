from collections.abc import Callable

from kafka_client_py import (
    AsyncPublisher,
    DLQPublisher,
    ProducerConfig,
    RetryPolicy,
    RetryPublisher,
)
from kafka_consumer_py import (
    ConsumerConfig,
    EventRouter,
    KafkaEventRouter,
    build_consumer_loop,
)

from ...config import get_worker_settings
from ._types import ProbesDictionary
from .transaction_events import (
    subscribe_transaction_created,
    subscribe_transaction_deleted,
    subscribe_transaction_updated,
)
from .user_events import subscribe_user_synced

_KNOWN_HANDLERS: list[Callable[[EventRouter, ProbesDictionary], None]] = [
    subscribe_user_synced,
    subscribe_transaction_created,
    subscribe_transaction_updated,
    subscribe_transaction_deleted,
]


async def build_event_router(config: ConsumerConfig) -> None:
    settings = get_worker_settings()
    router = KafkaEventRouter()
    _subscribe_all_events(router)

    publisher = AsyncPublisher(ProducerConfig(bootstrap_servers=config.bootstrap_servers))
    await publisher.start()

    try:
        consumer_loop = build_consumer_loop(
            config=config,
            router=router,
            retry_policy=RetryPolicy(),
            retry_publisher=RetryPublisher(publisher, topic=settings.kafka_retry_topic),
            dlq_publisher=DLQPublisher(publisher, topic=settings.kafka_dlq_topic),
        )
        await consumer_loop.run()
    finally:
        await publisher.stop()


def _subscribe_all_events(router: EventRouter) -> None:
    probes = _build_probes()
    for subscribe in _KNOWN_HANDLERS:
        subscribe(router, probes)


def _build_probes() -> ProbesDictionary:
    return ProbesDictionary.build_probes()

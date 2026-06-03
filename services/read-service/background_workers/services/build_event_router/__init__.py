from data_read_core.shared.health_guard import (
    PostgresHealthProbe,
    RedisHealthProbe,
)
from data_read_core.shared.kafka_updates import (
    ConsumerConfig,
    EventRouter,
    KafkaEventRouter,
    build_consumer_loop,
)
from kafka_client_py import (
    AsyncPublisher,
    DLQPublisher,
    ProducerConfig,
    RetryPolicy,
    RetryPublisher,
)

from .transaction_events import (
    subscribe_transaction_created,
    subscribe_transaction_deleted,
    subscribe_transaction_updated,
)
from .user_events import subscribe_user_synced
from .wallet_events import (
    subscribe_wallet_created,
    subscribe_wallet_deleted,
    subscribe_wallet_updated,
)


async def build_event_router(config: ConsumerConfig) -> None:
    router = KafkaEventRouter()
    _subscribe_all_events(router)

    publisher = AsyncPublisher(ProducerConfig(bootstrap_servers=config.bootstrap_servers))
    await publisher.start()

    try:
        consumer_loop = build_consumer_loop(
            config=config,
            router=router,
            retry_policy=RetryPolicy(),
            retry_publisher=RetryPublisher(publisher),
            dlq_publisher=DLQPublisher(publisher),
        )
        await consumer_loop.run()
    finally:
        await publisher.stop()


def _subscribe_all_events(router: EventRouter) -> None:
    postgres_probe = PostgresHealthProbe()
    redis_probe = RedisHealthProbe()

    subscribe_user_synced(router, postgres_probe)
    subscribe_wallet_deleted(router, postgres_probe, redis_probe)
    subscribe_wallet_updated(router, postgres_probe, redis_probe)
    subscribe_wallet_created(router, postgres_probe)
    subscribe_transaction_created(router, postgres_probe, redis_probe)
    subscribe_transaction_updated(router, postgres_probe, redis_probe)
    subscribe_transaction_deleted(router, postgres_probe, redis_probe)

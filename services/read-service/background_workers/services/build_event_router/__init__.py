import asyncio
from collections.abc import Callable

from data_read_core.shared.kafka_dedupe import DjangoDedupeStore
from django.conf import settings
from kafka_client_py import (
    AsyncPublisher,
    DLQPublisher,
    ProducerConfig,
    RetryPolicy,
    RetryPublisher,
)
from kafka_consumer_py import (
    ConsumerConfig,
    ConsumerLoop,
    EventRouter,
    KafkaEventRouter,
    SigtermShutdownSignal,
    build_consumer_loop,
    build_sandbox_traffic_policy,
)
from observability import KafkaMessageContextComponents, build_kafka_message_context_components

from ._types import ProbesDictionary, ProjectionRouters
from .account_events import (
    subscribe_account_created,
    subscribe_account_posting_created,
    subscribe_account_posting_deleted,
    subscribe_account_postings_dispatched,
    subscribe_account_updated,
)
from .action_events import subscribe_action_raised, subscribe_action_resolved
from .automation_events import (
    subscribe_automation_created,
    subscribe_automation_deleted,
    subscribe_automation_ran,
    subscribe_automation_updated,
)
from .goal_events import (
    subscribe_goal_created,
    subscribe_goal_deleted,
    subscribe_goal_updated,
)
from .notification_events import (
    subscribe_notification_created,
    subscribe_notification_deleted,
    subscribe_notifications_acknowledged,
)
from .transaction_events import (
    subscribe_transaction_created,
    subscribe_transaction_deleted,
    subscribe_transaction_metadata_updated,
    subscribe_transaction_updated,
)
from .user_events import subscribe_user_synced
from .wallet_events import (
    subscribe_wallet_created,
    subscribe_wallet_deleted,
    subscribe_wallet_updated,
)
from .webhook_events import (
    subscribe_webhook_created,
    subscribe_webhook_deleted,
    subscribe_webhook_subscription_added,
    subscribe_webhook_subscription_removed,
    subscribe_webhook_updated,
)

_KNOWN_HANDLERS: list[Callable[[ProjectionRouters, ProbesDictionary], None]] = [
    subscribe_user_synced,
    subscribe_account_created,
    subscribe_account_updated,
    subscribe_action_raised,
    subscribe_action_resolved,
    subscribe_automation_created,
    subscribe_automation_updated,
    subscribe_automation_deleted,
    subscribe_automation_ran,
    subscribe_account_posting_created,
    subscribe_account_posting_deleted,
    subscribe_account_postings_dispatched,
    subscribe_wallet_deleted,
    subscribe_wallet_updated,
    subscribe_wallet_created,
    subscribe_goal_created,
    subscribe_goal_updated,
    subscribe_goal_deleted,
    subscribe_transaction_created,
    subscribe_transaction_updated,
    subscribe_transaction_metadata_updated,
    subscribe_transaction_deleted,
    subscribe_notification_created,
    subscribe_notifications_acknowledged,
    subscribe_notification_deleted,
    subscribe_webhook_created,
    subscribe_webhook_updated,
    subscribe_webhook_deleted,
    subscribe_webhook_subscription_added,
    subscribe_webhook_subscription_removed,
]


async def build_event_router(
    postgres_config: ConsumerConfig,
    search_config: ConsumerConfig,
) -> None:
    routers = ProjectionRouters(postgres=KafkaEventRouter(), search=KafkaEventRouter())
    _subscribe_all_events(routers)

    message_context = build_kafka_message_context_components()
    publisher = AsyncPublisher(ProducerConfig(bootstrap_servers=postgres_config.bootstrap_servers))
    await publisher.start()

    shutdown = SigtermShutdownSignal()
    shutdown.install()

    try:
        lane_loops = [
            _build_lane_loop(
                postgres_config, routers.postgres, publisher, message_context, shutdown
            ),
            _build_lane_loop(search_config, routers.search, publisher, message_context, shutdown),
        ]
        async with asyncio.TaskGroup() as lanes:
            for lane_loop in lane_loops:
                lanes.create_task(lane_loop.run())
    finally:
        await publisher.stop()


def _build_lane_loop(
    config: ConsumerConfig,
    router: EventRouter,
    publisher: AsyncPublisher,
    message_context: KafkaMessageContextComponents,
    shutdown: SigtermShutdownSignal,
) -> ConsumerLoop:
    return build_consumer_loop(
        config=config,
        router=router,
        retry_policy=RetryPolicy(),
        retry_publisher=RetryPublisher(publisher, topic=settings.KAFKA["RETRY_TOPIC"]),
        dlq_publisher=DLQPublisher(publisher, topic=settings.KAFKA["DLQ_TOPIC"]),
        context_binder=message_context.context_binder,
        traffic_policy=build_sandbox_traffic_policy(
            config, message_context.traffic_policy.own_sandbox_id
        ),
        dedupe_store=DjangoDedupeStore(consumer_group=config.group_id),
        shutdown=shutdown,
        install_signal_handlers=False,
    )


def _subscribe_all_events(routers: ProjectionRouters) -> None:
    probes = _build_probes()
    for subscribe in _KNOWN_HANDLERS:
        subscribe(routers, probes)


def _build_probes() -> ProbesDictionary:
    return ProbesDictionary.build_probes()

import asyncio
import logging
from datetime import UTC, datetime

from data_read_core._shared.kafka_updates import (
    ConsumerConfig,
    EventMessage,
    EventRouter,
    KafkaEventRouter,
    build_consumer_loop,
)
from django.conf import settings
from django.core.management.base import BaseCommand
from kafka_client_py import (
    AsyncPublisher,
    DLQPublisher,
    ProducerConfig,
    RetryPolicy,
    RetryPublisher,
)

logger = logging.getLogger("background_workers.write_message_consumer")


class LoggingSettings:
    @staticmethod
    def enable_basic_config():
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )

    @staticmethod
    def forward_missed_messages():
        logging.getLogger("data_read_core._shared.kafka_updates").setLevel(logging.DEBUG)


class Command(BaseCommand):
    help = "Run a test Kafka consumer that logs every write-service event it receives."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--bootstrap-servers",
            default=settings.KAFKA["BOOTSTRAP_SERVERS"],
            help=f"Kafka bootstrap servers (default: {settings.KAFKA['BOOTSTRAP_SERVERS']}).",
        )
        parser.add_argument(
            "--topic",
            action="append",
            dest="topics",
            help=f"Topic to consume; repeatable (default: {settings.KAFKA['OUTBOX_TOPIC']}).",
        )
        parser.add_argument(
            "--group-id",
            default=settings.KAFKA["READ_GROUP_ID"],
            help=f"Consumer group id (default: {settings.KAFKA['READ_GROUP_ID']}).",
        )
        parser.add_argument(
            "--from-beginning",
            action="store_true",
            help="Read from the earliest offset instead of the latest.",
        )

    def handle(self, *args, **options) -> None:
        LoggingSettings.enable_basic_config()
        LoggingSettings.forward_missed_messages()

        topics = options["topics"] or [settings.KAFKA["OUTBOX_TOPIC"]]
        config = self._build_consumer_config(options, topics)

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting test consumer — servers={config.bootstrap_servers} "
                f"group={config.group_id} topics={list(topics)}"
            )
        )

        try:
            asyncio.run(self._run(config))
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Interrupted — shutting down."))

    def _build_consumer_config(self, options, topics):
        return ConsumerConfig(
            bootstrap_servers=options["bootstrap_servers"],
            group_id=options["group_id"],
            topics=topics,
            auto_offset_reset="earliest" if options["from_beginning"] else "latest",
        )

    async def _run(self, config: ConsumerConfig) -> None:
        router = KafkaEventRouter()
        self._subscribe_all_events(router)

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

    def _subscribe_all_events(self, router: EventRouter) -> None:
        for event_type in (
            "WalletCreated",
            "WalletUpdated",
            "WalletDeleted",
            "TransactionCreated",
            "TransactionDeleted",
            "WebhookDeliveryStatusChanged",
        ):
            router.register(event_type, self._log_event)

    async def _log_event(self, event: EventMessage) -> None:
        received_at = datetime.now(UTC).isoformat()
        logger.info(
            "[%s] received %s | aggregate=%s/%s event_id=%s outbox_seq=%s "
            "topic=%s partition=%s offset=%s payload_bytes=%d",
            received_at,
            event.event_type,
            event.aggregate_type,
            event.aggregate_id,
            event.event_id,
            event.outbox_seq,
            event.topic,
            event.partition,
            event.offset,
            len(event.payload),
        )

import asyncio
import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from kafka_consumer_py import ConsumerConfig

from background_workers.services.build_event_router import build_event_router

logger = logging.getLogger("background_workers.write_message_consumer")


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
        topics = options["topics"] or [
            settings.KAFKA["OUTBOX_TOPIC"],
            settings.KAFKA["RETRY_TOPIC"],
        ]
        config = self._build_consumer_config(options, topics)

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting test consumer — servers={config.bootstrap_servers} "
                f"group={config.group_id} topics={list(topics)}"
            )
        )

        try:
            asyncio.run(build_event_router(config))
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Interrupted — shutting down."))

    def _build_consumer_config(self, options, topics) -> ConsumerConfig:
        return ConsumerConfig(
            bootstrap_servers=options["bootstrap_servers"],
            group_id=options["group_id"],
            topics=topics,
            auto_offset_reset="earliest" if options["from_beginning"] else "latest",
        )

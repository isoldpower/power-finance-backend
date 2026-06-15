import asyncio

from django.conf import settings
from django.core.management.base import BaseCommand

from background_workers.services.inbound_notifications import (
    InboundConsumerConfig,
    run_inbound_notifications_consumer,
)


class Command(BaseCommand):
    help = (
        "Consume NotificationRequested messages from the inbound notifications "
        "topic and persist them through the CreateNotification command."
    )

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
            help=(
                "Topic to consume; repeatable "
                f"(default: {settings.KAFKA['NOTIFICATIONS_INBOUND_TOPIC']})."
            ),
        )
        parser.add_argument(
            "--group-id",
            default=settings.KAFKA["NOTIFICATIONS_INBOUND_GROUP_ID"],
            help=(
                "Consumer group id "
                f"(default: {settings.KAFKA['NOTIFICATIONS_INBOUND_GROUP_ID']})."
            ),
        )

    def handle(self, *args, **options) -> None:
        topics = options["topics"] or [settings.KAFKA["NOTIFICATIONS_INBOUND_TOPIC"]]
        config = InboundConsumerConfig(
            bootstrap_servers=options["bootstrap_servers"],
            group_id=options["group_id"],
            topics=topics,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting inbound notifications consumer — "
                f"servers={config.bootstrap_servers} group={config.group_id} "
                f"topics={list(topics)}"
            )
        )

        try:
            asyncio.run(run_inbound_notifications_consumer(config))
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Interrupted — shutting down."))

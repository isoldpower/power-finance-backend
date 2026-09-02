import asyncio

from django.conf import settings
from django.core.management.base import BaseCommand

from background_workers.services.automation_engine import (
    AutomationEngineConfig,
    run_automation_engine,
)


class Command(BaseCommand):
    help = (
        "Run user-authored rules whose trigger is an event: consume transaction "
        "events off the outbox topic and apply the effects of every matching rule."
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
            help=f"Topic to consume; repeatable (default: {settings.KAFKA['OUTBOX_TOPIC']}).",
        )
        parser.add_argument(
            "--group-id",
            default=settings.KAFKA["AUTOMATION_ENGINE_GROUP_ID"],
            help=f"Consumer group id (default: {settings.KAFKA['AUTOMATION_ENGINE_GROUP_ID']}).",
        )

    def handle(self, *args, **options) -> None:
        topics = options["topics"] or [settings.KAFKA["OUTBOX_TOPIC"]]
        config = AutomationEngineConfig(
            bootstrap_servers=options["bootstrap_servers"],
            group_id=options["group_id"],
            topics=topics,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting automation engine — servers={config.bootstrap_servers} "
                f"group={config.group_id} topics={list(topics)}"
            )
        )

        try:
            asyncio.run(run_automation_engine(config))
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Interrupted — shutting down."))

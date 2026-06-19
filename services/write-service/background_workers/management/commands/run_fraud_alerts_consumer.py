import asyncio

from django.conf import settings
from django.core.management.base import BaseCommand

from background_workers.services.fraud_alerts import (
    FraudAlertsConsumerConfig,
    run_fraud_alerts_consumer,
)


class Command(BaseCommand):
    help = (
        "Consume fraud alerts emitted by the antifraud service and record the "
        "suspended users in Redis."
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
                f"(default: {settings.KAFKA['FRAUD_ALERTS_TOPIC']})."
            ),
        )
        parser.add_argument(
            "--group-id",
            default=settings.KAFKA["FRAUD_ALERTS_GROUP_ID"],
            help=("Consumer group id " f"(default: {settings.KAFKA['FRAUD_ALERTS_GROUP_ID']})."),
        )

    def handle(self, *args, **options) -> None:
        topics = options["topics"] or [settings.KAFKA["FRAUD_ALERTS_TOPIC"]]
        config = FraudAlertsConsumerConfig(
            bootstrap_servers=options["bootstrap_servers"],
            group_id=options["group_id"],
            topics=topics,
            redis_host=settings.REDIS["HOST"],
            redis_port=int(settings.REDIS["PORT"]),
            redis_password=settings.REDIS["PASSWORD"],
            redis_db=int(settings.FRAUD["REDIS_DB"]),
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting fraud alerts consumer — "
                f"servers={config.bootstrap_servers} group={config.group_id} "
                f"topics={list(topics)}"
            )
        )

        try:
            asyncio.run(run_fraud_alerts_consumer(config))
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Interrupted — shutting down."))

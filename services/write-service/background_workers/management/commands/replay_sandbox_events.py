import asyncio
import json
from datetime import datetime

from data_write_core.infrastructure.orm import OutboxEntryModel
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from kafka_client_py import AsyncPublisher, ProducerConfig

SANDBOX_BAGGAGE_KEY = "sandbox-id"


class Command(BaseCommand):
    help = (
        "Re-publish a sandbox's outbox events so the baseline projects them. "
        "An isolated sandbox applies the events it claims into its OWN datastores, "
        "and the baseline consumer skips them, so the baseline read model is left "
        "with a permanent hole. This fills it from the outbox, which is the durable "
        "record and outlives the topic's seven-day retention."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument("--sandbox", required=True, help="Sandbox id to replay.")
        parser.add_argument(
            "--since",
            default=None,
            help="Only events at or after this ISO-8601 timestamp.",
        )
        parser.add_argument(
            "--until",
            default=None,
            help="Only events at or before this ISO-8601 timestamp.",
        )
        parser.add_argument(
            "--list-only",
            action="store_true",
            help="Print the event ids that would be replayed and publish nothing.",
        )
        parser.add_argument(
            "--keep-sandbox-baggage",
            action="store_true",
            help=(
                "Leave sandbox-id in the baggage. The baseline then claims the event "
                "only while no consumer group for that sandbox exists, so the replay "
                "silently does nothing if the sandbox is still up."
            ),
        )
        parser.add_argument(
            "--bootstrap-servers",
            default=settings.KAFKA["BOOTSTRAP_SERVERS"],
            help=f"Kafka bootstrap servers (default: {settings.KAFKA['BOOTSTRAP_SERVERS']}).",
        )
        parser.add_argument(
            "--topic",
            default=settings.KAFKA["OUTBOX_TOPIC"],
            help=f"Topic to publish to (default: {settings.KAFKA['OUTBOX_TOPIC']}).",
        )

    def handle(self, *args, **options) -> None:
        entries = list(_select_entries(options))
        if not entries:
            raise CommandError(
                f"No outbox events carry sandbox-id={options['sandbox']}. "
                "Either the sandbox produced none, or its events predate the "
                "baggage column."
            )

        if options["list_only"]:
            for entry in entries:
                self.stdout.write(str(entry.event_id))

            return

        asyncio.run(_publish(entries, options))
        self.stdout.write(
            self.style.SUCCESS(f"replayed {len(entries)} event(s) to {options['topic']}")
        )


def _select_entries(options):
    queryset = OutboxEntryModel.objects.filter(
        baggage__contains=f"{SANDBOX_BAGGAGE_KEY}={options['sandbox']}"
    )
    if options["since"]:
        queryset = queryset.filter(occurred_at__gte=datetime.fromisoformat(options["since"]))
    if options["until"]:
        queryset = queryset.filter(occurred_at__lte=datetime.fromisoformat(options["until"]))

    return queryset.order_by("id")


async def _publish(entries, options) -> None:
    config = ProducerConfig(
        bootstrap_servers=options["bootstrap_servers"],
        client_id="write-service.sandbox-replay",
    )
    async with AsyncPublisher(config) as publisher:
        for entry in entries:
            await publisher.publish(
                options["topic"],
                value=json.dumps(entry.payload).encode(),
                key=entry.partition_key.encode() if entry.partition_key else None,
                headers=_headers(entry, keep_sandbox=options["keep_sandbox_baggage"]),
            )


def _headers(entry, keep_sandbox: bool):
    """The envelope headers a replayed message carries.

    Debezium's EventRouter builds these from the outbox row, and a replayed
    message has to be indistinguishable from one it produced — same event_id
    above all, because that is what every consumer's dedupe keys on, and what
    stops the services that already applied this event from applying it twice.
    """

    baggage = entry.baggage if keep_sandbox else _without_sandbox(entry.baggage)
    candidates = (
        ("event_id", str(entry.event_id)),
        ("aggregate_type", entry.aggregate_type),
        ("event_type", entry.event_type),
        ("outbox_seq", str(entry.id)),
        ("traceparent", entry.traceparent),
        ("tracestate", entry.tracestate),
        ("baggage", baggage),
    )

    return [(name, value.encode()) for name, value in candidates if value]


def _without_sandbox(baggage: str | None) -> str | None:
    if not baggage:
        return baggage

    kept = [
        member
        for member in baggage.split(",")
        if not member.strip().startswith(f"{SANDBOX_BAGGAGE_KEY}=")
    ]

    return ",".join(kept) or None

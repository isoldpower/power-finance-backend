import logging

from data_read_core.shared.elasticsearch import get_elasticsearch
from django.core.management import call_command
from django.core.management.base import BaseCommand

logger = logging.getLogger("background_workers.elastic_backfill")

BACKFILL_COMMANDS = (
    "backfill_wallet_balances",
    "backfill_search_documents",
)


class Command(BaseCommand):
    help = (
        "Restate every Elasticsearch document from the Postgres read model — "
        "wallet balances, then automations, goals and transactions. Use after "
        "an Elasticsearch outage, after changing how a document is built, or "
        "to repair drift. Idempotent, and safe to run while the consumer is "
        "live: each document is rewritten from the row it belongs to."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--include-deleted",
            action="store_true",
            help="Also restate rows that have been soft deleted.",
        )

    def handle(self, *args, **options) -> None:
        """Run each per-index backfill in turn, on a fresh Elasticsearch client."""
        for command_name in BACKFILL_COMMANDS:
            self.stdout.write(self.style.MIGRATE_HEADING(f"Running {command_name}…"))
            get_elasticsearch.cache_clear()
            call_command(
                command_name,
                include_deleted=options["include_deleted"],
                stdout=self.stdout,
                stderr=self.stderr,
            )

        self.stdout.write(self.style.SUCCESS("Elasticsearch restated from Postgres."))

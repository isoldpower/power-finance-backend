import logging

from data_read_core.shared.elasticsearch import get_elasticsearch
from django.core.management import call_command
from django.core.management.base import BaseCommand

logger = logging.getLogger("background_workers.elastic_backfill")

# Postgres is the source of truth for every indexed value, so repairing a drifted
# index is always "rewrite the document from its row". The per-index work already
# lives in the two commands below; this one exists so that repairing *everything*
# is a single call rather than a list to remember under pressure.
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
        for command_name in BACKFILL_COMMANDS:
            self.stdout.write(self.style.MIGRATE_HEADING(f"Running {command_name}…"))
            # Each sub-command owns an asyncio.run() of its own and closes the
            # client it used. The factory is lru_cached, so without dropping the
            # cache the next command inherits a client bound to a dead event loop
            # and aiohttp refuses it.
            get_elasticsearch.cache_clear()
            call_command(
                command_name,
                include_deleted=options["include_deleted"],
                stdout=self.stdout,
                stderr=self.stderr,
            )

        self.stdout.write(self.style.SUCCESS("Elasticsearch restated from Postgres."))

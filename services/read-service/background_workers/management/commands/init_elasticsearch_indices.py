import asyncio
import logging

from data_read_core.shared.elasticsearch import INDEX_DEFINITIONS, get_elasticsearch
from django.core.management.base import BaseCommand
from elasticsearch import AsyncElasticsearch

logger = logging.getLogger("background_workers.elasticsearch_init")


class Command(BaseCommand):
    help = (
        "Create the read-side Elasticsearch indices (wallets, transactions) with "
        "their mappings. Idempotent: existing indices are left untouched unless "
        "--recreate is passed."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--recreate",
            action="store_true",
            help="Drop and recreate each index. DESTROYS all indexed documents.",
        )

    def handle(self, *args, **options) -> None:
        asyncio.run(self._run(recreate=options["recreate"]))

    async def _run(self, *, recreate: bool) -> None:
        client = get_elasticsearch()

        try:
            await asyncio.gather(
                *[
                    self._ensure_index(
                        client,
                        index_name,
                        definition,
                        recreate=recreate,
                    )
                    for index_name, definition in INDEX_DEFINITIONS.items()
                ]
            )
        finally:
            await client.close()

    async def _ensure_index(
        self,
        client: AsyncElasticsearch,
        index_name: str,
        definition: dict,
        *,
        recreate: bool,
    ) -> None:
        exists = bool(await client.indices.exists(index=index_name))

        if exists and recreate:
            await client.indices.delete(index=index_name)
            self.stdout.write(self.style.WARNING(f"Dropped index {index_name}."))
            exists = False

        if exists:
            self.stdout.write(f"Index {index_name} already exists; skipping.")
            return

        await client.indices.create(index=index_name, **definition)
        self.stdout.write(self.style.SUCCESS(f"Created index {index_name}."))

import asyncio
import logging

from asgiref.sync import sync_to_async
from data_read_core.shared.elasticsearch import WALLETS_INDEX, get_elasticsearch
from data_read_core.shared.postgres_orm import WalletReadModel
from django.core.management.base import BaseCommand
from elasticsearch import NotFoundError

logger = logging.getLogger("background_workers.wallet_balance_backfill")

BATCH_SIZE = 500


class Command(BaseCommand):
    help = (
        "Restate the balance and zero_balance of every wallet document in "
        "Elasticsearch from the Postgres read model. Use after enabling the "
        "indexed balance, or to repair drift. Idempotent."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--include-deleted",
            action="store_true",
            help="Also restate wallets that have been soft deleted.",
        )

    def handle(self, *args, **options) -> None:
        restated, missing = asyncio.run(
            self._run(include_deleted=options["include_deleted"]),
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Restated {restated} wallet document(s); {missing} had no document to update."
            )
        )

    async def _run(self, *, include_deleted: bool) -> tuple[int, int]:
        client = get_elasticsearch()
        restated = 0
        missing = 0

        try:
            async for wallet in self._wallets(include_deleted=include_deleted):
                identifier, balance, zero_balance = wallet
                try:
                    await client.update(
                        index=WALLETS_INDEX,
                        id=str(identifier),
                        doc={
                            "balance": float(balance),
                            "zero_balance": float(zero_balance),
                        },
                    )
                except NotFoundError:
                    missing += 1
                    logger.warning("No wallet document %s to restate.", identifier)
                    continue

                restated += 1
                logger.info("Restated wallet %s to balance %s.", identifier, balance)
        finally:
            await client.close()

        return restated, missing

    async def _wallets(self, *, include_deleted: bool):
        offset = 0

        while True:
            page = await sync_to_async(self._page)(
                include_deleted=include_deleted,
                offset=offset,
            )
            if not page:
                return

            for row in page:
                yield row

            offset += len(page)

    def _page(self, *, include_deleted: bool, offset: int) -> list[tuple]:
        queryset = WalletReadModel.objects.all()
        if not include_deleted:
            queryset = queryset.filter(deleted_at__isnull=True)

        return list(
            queryset.order_by("id").values_list("id", "balance", "zero_balance")[
                offset : offset + BATCH_SIZE
            ]
        )

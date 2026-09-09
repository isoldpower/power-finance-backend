import asyncio
import logging

from asgiref.sync import sync_to_async
from data_read_core.shared.elasticsearch import (
    AUTOMATIONS_INDEX,
    GOALS_INDEX,
    get_elasticsearch,
)
from data_read_core.shared.postgres_orm import AutomationReadModel, GoalReadModel
from data_read_core.shared.timestamps import to_iso
from django.core.management.base import BaseCommand
from elasticsearch import AsyncElasticsearch

logger = logging.getLogger("background_workers.search_document_backfill")

BATCH_SIZE = 500

AUTOMATIONS_RESOURCE = "automations"
GOALS_RESOURCE = "goals"
KNOWN_RESOURCES = (AUTOMATIONS_RESOURCE, GOALS_RESOURCE)


class Command(BaseCommand):
    help = (
        "Seed the automation and goal Elasticsearch indices from the Postgres "
        "read models. Use once after the indices are created, or to repair "
        "drift. Idempotent: every document is rewritten from the row it "
        "belongs to."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--resource",
            choices=KNOWN_RESOURCES,
            action="append",
            help="Backfill only this resource. Repeatable. Default: all of them.",
        )
        parser.add_argument(
            "--include-deleted",
            action="store_true",
            help="Also index rows that have been soft deleted.",
        )

    def handle(self, *args, **options) -> None:
        chosen_resources = options["resource"] or list(KNOWN_RESOURCES)
        indexed_counts = asyncio.run(
            self._run(
                chosen_resources=chosen_resources,
                include_deleted=options["include_deleted"],
            )
        )

        for resource, indexed in indexed_counts.items():
            self.stdout.write(self.style.SUCCESS(f"Indexed {indexed} {resource} document(s)."))

    async def _run(
        self,
        *,
        chosen_resources: list[str],
        include_deleted: bool,
    ) -> dict[str, int]:
        client = get_elasticsearch()
        indexed_counts: dict[str, int] = {}

        try:
            if AUTOMATIONS_RESOURCE in chosen_resources:
                indexed_counts[AUTOMATIONS_RESOURCE] = await self._backfill(
                    client,
                    index_name=AUTOMATIONS_INDEX,
                    rows=self._automation_rows(include_deleted=include_deleted),
                    build_document=automation_document,
                )

            if GOALS_RESOURCE in chosen_resources:
                indexed_counts[GOALS_RESOURCE] = await self._backfill(
                    client,
                    index_name=GOALS_INDEX,
                    rows=self._goal_rows(include_deleted=include_deleted),
                    build_document=goal_document,
                )
        finally:
            await client.close()

        return indexed_counts

    async def _backfill(
        self,
        client: AsyncElasticsearch,
        *,
        index_name: str,
        rows,
        build_document,
    ) -> int:
        indexed = 0

        async for row in rows:
            await client.index(
                index=index_name,
                id=str(row.id),
                document=build_document(row),
            )
            indexed += 1
            logger.info("Backfilled %s into %s.", row.id, index_name)

        await client.indices.refresh(index=index_name)
        return indexed

    async def _automation_rows(self, *, include_deleted: bool):
        async for row in self._paged(AutomationReadModel, include_deleted=include_deleted):
            yield row

    async def _goal_rows(self, *, include_deleted: bool):
        async for row in self._paged(GoalReadModel, include_deleted=include_deleted):
            yield row

    async def _paged(self, model, *, include_deleted: bool):
        offset = 0

        while True:
            page = await sync_to_async(self._page)(
                model,
                include_deleted=include_deleted,
                offset=offset,
            )
            if not page:
                return

            for row in page:
                yield row

            offset += len(page)

    def _page(self, model, *, include_deleted: bool, offset: int) -> list:
        queryset = model.objects.all()
        if not include_deleted:
            queryset = queryset.filter(deleted_at__isnull=True)

        return list(queryset.order_by("id")[offset : offset + BATCH_SIZE])


def automation_document(automation: AutomationReadModel) -> dict:
    return {
        "id": str(automation.id),
        "user_id": automation.user_id,
        "name": automation.name,
        "icon": automation.icon,
        "enabled": automation.enabled,
        "trigger_type": automation.trigger_type,
        "trigger_event": automation.trigger_event,
        "trigger_schedule": automation.trigger_schedule,
        "filter_body": automation.filter_body,
        "effects": list(automation.effects or []),
        "runs": automation.runs,
        "last_run_at": to_iso(automation.last_run_at),
        "created_at": to_iso(automation.created_at),
        "updated_at": to_iso(automation.updated_at),
        "deleted_at": to_iso(automation.deleted_at),
    }


def goal_document(goal: GoalReadModel) -> dict:
    return {
        "id": str(goal.id),
        "user_id": goal.user_id,
        "title": goal.title,
        "currency_code": goal.currency_code,
        "target": float(goal.target),
        "progress": float(goal.progress),
        "url": goal.url or None,
        "finish_at": to_iso(goal.finish_at),
        "created_at": to_iso(goal.created_at),
        "updated_at": to_iso(goal.updated_at),
        "deleted_at": to_iso(goal.deleted_at),
    }

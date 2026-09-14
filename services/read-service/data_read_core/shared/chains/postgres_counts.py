from collections.abc import Iterable

from django.db.models import Count

from data_read_core.shared.postgres_orm import TransactionReadModel


async def fetch_chain_sizes(chain_ids: Iterable[str | None]) -> dict[str, int]:
    wanted = {chain_id for chain_id in chain_ids if chain_id}
    if not wanted:
        return {}

    grouped = (
        TransactionReadModel.objects.filter(
            chain_id__in=wanted,
            deleted_at__isnull=True,
        )
        .values("chain_id")
        .annotate(size=Count("id"))
    )

    return {str(row["chain_id"]): row["size"] async for row in grouped}

from typing import Any

from data_read_core.shared.elasticsearch import TRANSACTIONS_INDEX, get_elasticsearch
from data_read_core.shared.pagination import PageRequest, elasticsearch_page_arguments


async def search_owned_transactions(
    user_id: int,
    filter_query: dict[str, Any],
    page: PageRequest,
) -> tuple[list[dict[str, Any]], int]:
    """Run the resolved filter against the transactions index, fenced to the
    requesting user. Returns (hit sources, total)."""

    response = await get_elasticsearch().search(
        index=TRANSACTIONS_INDEX,
        query={
            "bool": {
                "must": [filter_query],
                "filter": [{"term": {"user_id": user_id}}],
            }
        },
        **elasticsearch_page_arguments(page),
    )

    hits = response["hits"]
    return (
        [hit["_source"] for hit in hits["hits"]],
        hits["total"]["value"],
    )

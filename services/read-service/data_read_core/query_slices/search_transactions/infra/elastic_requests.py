from collections.abc import Iterable
from typing import Any

from data_read_core.shared.elasticsearch import TRANSACTIONS_INDEX, get_elasticsearch
from data_read_core.shared.pagination import PageRequest, elasticsearch_page_arguments


async def search_owned_transactions(
    user_id: int,
    filter_query: dict[str, Any],
    page: PageRequest,
) -> tuple[list[dict[str, Any]], int]:
    response = await get_elasticsearch().search(
        index=TRANSACTIONS_INDEX,
        query={
            "bool": {
                "must": [filter_query],
                "filter": [{"term": {"user_id": user_id}}],
                "must_not": [{"exists": {"field": "deleted_at"}}],
            }
        },
        **elasticsearch_page_arguments(page),
    )

    hits = response["hits"]
    return (
        [hit["_source"] for hit in hits["hits"]],
        hits["total"]["value"],
    )


async def count_chain_members(chain_ids: Iterable[str | None]) -> dict[str, int]:
    wanted = sorted({chain_id for chain_id in chain_ids if chain_id})
    if not wanted:
        return {}

    response = await get_elasticsearch().search(
        index=TRANSACTIONS_INDEX,
        size=0,
        query={
            "bool": {
                "filter": [{"terms": {"chain_id": wanted}}],
                "must_not": [{"exists": {"field": "deleted_at"}}],
            }
        },
        aggregations={"chains": {"terms": {"field": "chain_id", "size": len(wanted)}}},
    )

    return {
        bucket["key"]: bucket["doc_count"]
        for bucket in response["aggregations"]["chains"]["buckets"]
    }

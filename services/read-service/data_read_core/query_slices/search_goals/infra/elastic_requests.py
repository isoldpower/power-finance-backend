from typing import Any

from data_read_core.shared.elasticsearch import GOALS_INDEX, get_elasticsearch
from data_read_core.shared.pagination import PageRequest, elasticsearch_page_arguments


async def search_owned_goals(
    user_id: int,
    filter_query: dict[str, Any],
    page: PageRequest,
) -> tuple[list[dict[str, Any]], int]:
    response = await get_elasticsearch().search(
        index=GOALS_INDEX,
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

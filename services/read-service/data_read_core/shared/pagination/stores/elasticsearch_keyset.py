from typing import Any

from ..page_request import PageRequest

SORT_ARGUMENT = "sort"
SIZE_ARGUMENT = "size"
TRACK_TOTAL_HITS_ARGUMENT = "track_total_hits"
SEARCH_AFTER_ARGUMENT = "search_after"


def elasticsearch_page_arguments(request: PageRequest) -> dict[str, Any]:
    arguments: dict[str, Any] = {
        SORT_ARGUMENT: request.read_order.elasticsearch_sort,
        SIZE_ARGUMENT: request.fetch_size,
        TRACK_TOTAL_HITS_ARGUMENT: True,
    }

    anchor = request.elasticsearch_anchor
    if anchor is not None:
        arguments[SEARCH_AFTER_ARGUMENT] = anchor

    return arguments

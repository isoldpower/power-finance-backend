from typing import Any
from django.db.models import Q

from .filter_parser import FilterTree
from ..entities import FilterPolicy


def resolve_filter_query(
        query: dict[str, Any],
        filter_policy: FilterPolicy
) -> Q:
    filter_tree = FilterTree(filter_policy)
    return filter_tree.resolve(query)

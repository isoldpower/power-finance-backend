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


def resolve_filter_query_sql(
        query: dict[str, Any],
        filter_policy: FilterPolicy
) -> tuple[str, dict]:
    filter_tree = FilterTree(filter_policy)
    return filter_tree.resolve_sql(query)

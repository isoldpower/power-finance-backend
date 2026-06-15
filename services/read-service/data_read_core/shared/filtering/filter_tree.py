from typing import Any

from django.db.models import Q

from .entities import FilterPolicy
from .tree_builder import TreeBuilder


class FilterTree:
    """Resolves a raw filter dict against a per-field policy into a Django ORM
    predicate (resolve) or an Elasticsearch query clause (resolve_es)."""

    def __init__(self, policy: FilterPolicy) -> None:
        self._builder = TreeBuilder(policy)

    def resolve(self, raw: dict[str, Any]) -> Q:
        return self._builder.build(raw).resolve()

    def resolve_es(self, raw: dict[str, Any]) -> dict[str, Any]:
        return self._builder.build(raw).resolve_es()

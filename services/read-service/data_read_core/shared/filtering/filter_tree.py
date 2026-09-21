from typing import Any

from django.db.models import Q
from filter_grammar_py import ROOT_PATH, FilterPolicy

from .tree_builder import TreeBuilder


class FilterTree:
    def __init__(self, policy: FilterPolicy) -> None:
        self._builder = TreeBuilder(policy)

    def resolve(self, raw: dict[str, Any], path: str = ROOT_PATH) -> Q:
        return self._builder.build(raw, path).resolve()

    def resolve_es(self, raw: dict[str, Any], path: str = ROOT_PATH) -> dict[str, Any]:
        return self._builder.build(raw, path).resolve_es()

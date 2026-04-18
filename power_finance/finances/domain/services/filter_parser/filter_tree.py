from typing import Any
from django.db.models import Q

from .abstraction import TreeNode
from .tree_builder import TreeBuilder
from ...entities import FilterPolicy


class FilterTree:
    _head: TreeNode
    _builder: TreeBuilder

    def __init__(
            self,
            policy: FilterPolicy
    ) -> None:
        self._builder = TreeBuilder(policy)

    def resolve(self, raw: dict[str, Any]) -> Q:
        tree_head = self._builder.build_tree(raw)

        return tree_head.resolve()

    def resolve_sql(self, raw: dict[str, Any]) -> str:
        tree_head = self._builder.build_tree(raw)

        return tree_head.resolve_sql()

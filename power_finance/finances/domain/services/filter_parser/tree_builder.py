from typing import Any, Optional

from .abstraction import TreeNode
from .exceptions import InvalidOperationError
from .group_nodes import GroupNodeBuilder, FilterGroupNodeBuilder, StandardGroupNodeBuilder
from .leaf_nodes import LeafNodeBuilder, FilterLeafNodeBuilder, StandardLeafTreeNodeBuilder
from ...entities import FieldFilter, ComparisonOperator, FilterPolicy


class TreeBuilder:
    _leaf_builder: LeafNodeBuilder
    _group_builder: GroupNodeBuilder
    _policy: FilterPolicy

    def __init__(
            self,
            policy: FilterPolicy | None = None,
            leaf_builder: LeafNodeBuilder | None = None,
            group_builder: GroupNodeBuilder | None = None,
    ):
        if policy:
            self._leaf_builder = leaf_builder or FilterLeafNodeBuilder(policy)
            self._group_builder = group_builder or FilterGroupNodeBuilder()
        else:
            self._leaf_builder = leaf_builder or StandardLeafTreeNodeBuilder()
            self._group_builder = group_builder or StandardGroupNodeBuilder()

    def _build_nodes(
            self,
            raw_value: dict[str, Any],
            policy: Optional[FilterPolicy] = None
    ) -> list[TreeNode]:
        if self._group_builder.is_group(raw_value):
            self._group_builder.validate(raw_value)
            operator, children_raw = self._group_builder.parse_raw(raw_value)
            children_nodes = [self._build_nodes(
                child_raw,
                policy
            ) for child_raw in children_raw]
            children_flat = [
                children_node for subtree in children_nodes
                for children_node in subtree
            ]

            return [self._group_builder.get_related_group(children_flat, operator)]

        elif self._leaf_builder.is_leaf(raw_value):
            field_name = raw_value.get("field_name")

            return [
                self._leaf_builder.get_related_leaf(FieldFilter(
                    value=raw_value.get("value"),
                    operator=ComparisonOperator(raw_value.get("operator")),
                    field_name=field_name
                ),
            )]

        raise InvalidOperationError(f"Unknown structure as the dictionary passed was neither a leaf nor a group: {raw_value}")

    def build_tree(
            self,
            raw_value: dict[str, Any],
            policy: Optional[FilterPolicy] = None
    ) -> TreeNode:
        return self._build_nodes(raw_value, policy)[0]
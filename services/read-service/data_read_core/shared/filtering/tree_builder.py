from typing import Any

from .abstraction import TreeNode
from .entities import ComparisonOperator, FieldFilter, FilterPolicy
from .exceptions import InvalidOperationError, InvalidStructureError
from .group_nodes import FilterGroupNodeBuilder
from .leaf_nodes import FilterLeafNodeBuilder


class TreeBuilder:
    """Parses a raw filter dict into a tree of TreeNodes, delegating leaf and
    group recognition to their respective builders."""

    def __init__(self, policy: FilterPolicy) -> None:
        self._leaf_builder = FilterLeafNodeBuilder(policy)
        self._group_builder = FilterGroupNodeBuilder()

    def build(self, raw: dict[str, Any]) -> TreeNode:
        if not isinstance(raw, dict):
            raise InvalidStructureError(f"Filter node must be an object, got: {raw!r}")

        if self._group_builder.is_group(raw):
            self._group_builder.validate(raw)
            operator, children_raw = self._group_builder.parse_raw(raw)
            children = [self.build(child) for child in children_raw]

            return self._group_builder.get_related_group(children, operator)

        if self._leaf_builder.is_leaf(raw):
            return self._leaf_builder.get_related_leaf(self._parse_field_filter(raw))

        raise InvalidOperationError(
            f"Unknown structure as the dictionary passed was neither a leaf nor a group: {raw}"
        )

    @staticmethod
    def _parse_field_filter(raw: dict[str, Any]) -> FieldFilter:
        try:
            operator = ComparisonOperator(raw["operator"])
        except ValueError as exc:
            raise InvalidOperationError(f"Unknown operator type: {raw['operator']}") from exc

        return FieldFilter(
            field_name=raw["field_name"],
            operator=operator,
            value=raw["value"],
        )

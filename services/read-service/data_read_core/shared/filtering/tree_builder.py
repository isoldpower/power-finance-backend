from typing import Any

from .abstraction import TreeNode
from .entities import ComparisonOperator, FieldFilter, FilterPolicy
from .exceptions import ROOT_PATH, InvalidOperationError, InvalidStructureError, UnknownNodeError
from .group_nodes import FilterGroupNodeBuilder
from .leaf_nodes import FilterLeafNodeBuilder


class TreeBuilder:
    """Parses a raw filter dict into a tree of TreeNodes, delegating leaf and
    group recognition to their respective builders."""

    def __init__(self, policy: FilterPolicy) -> None:
        self._leaf_builder = FilterLeafNodeBuilder(policy)
        self._group_builder = FilterGroupNodeBuilder()

    def build(self, raw: dict[str, Any], path: str = ROOT_PATH) -> TreeNode:
        if not isinstance(raw, dict):
            raise InvalidStructureError(
                f"Filter node must be an object, got {type(raw).__name__}", path=path
            )

        if self._group_builder.is_group(raw):
            self._group_builder.validate(raw, path)
            operator, children_raw = self._group_builder.parse_raw(raw, path)
            children = [
                self.build(child, f"{path}.{operator.value}[{index}]")
                for index, child in enumerate(children_raw)
            ]

            return self._group_builder.get_related_group(
                children,
                operator,
                path,
            )

        if self._leaf_builder.is_leaf(raw, path):
            return self._leaf_builder.get_related_leaf(
                self._parse_field_filter(raw, path),
                path,
            )

        raise UnknownNodeError(
            "Node is neither a valid group nor a valid leaf",
            path=path,
        )

    @staticmethod
    def _parse_field_filter(raw: dict[str, Any], path: str) -> FieldFilter:
        try:
            operator = ComparisonOperator(raw["operator"])
        except ValueError as exc:
            raise InvalidOperationError(
                f"Unknown operator {raw['operator']!r}",
                path=f"{path}.operator",
            ) from exc

        return FieldFilter(
            field_name=raw["field_name"],
            operator=operator,
            value=raw["value"],
        )

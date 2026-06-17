from typing import Any

from ..abstraction import TreeNode
from ..entities import GroupOperator
from ..exceptions import InvalidGroupingError, InvalidStructureError
from .abstraction import GroupNodeBuilder, GroupTreeNode
from .and_group import AndGroupTreeNode
from .or_group import OrGroupTreeNode


class FilterGroupNodeBuilder(GroupNodeBuilder):
    _known_groups: tuple[type[GroupTreeNode], ...] = (
        AndGroupTreeNode,
        OrGroupTreeNode,
    )

    def is_group(self, raw: dict[str, Any]) -> bool:
        return any(group.operator.value in raw for group in self._known_groups)

    def validate(self, raw: dict[str, Any]) -> None:
        present = [group for group in self._known_groups if group.operator.value in raw]
        if len(present) != 1 or len(raw) != 1:
            raise InvalidGroupingError("Filter grouping is breaking one or more constraints")

    def parse_raw(self, raw: dict[str, Any]) -> tuple[GroupOperator, list[dict[str, Any]]]:
        operator_key = next(iter(raw))
        children = raw[operator_key]
        if not isinstance(children, list) or not children:
            raise InvalidStructureError(
                "Filtering group must have non-empty list of conditions as value"
            )

        return GroupOperator(operator_key), children

    def get_related_group(self, children: list[TreeNode], operator: GroupOperator) -> GroupTreeNode:
        for group in self._known_groups:
            if group.is_related(operator):
                return group(children)

        raise InvalidGroupingError(f"Unknown filter grouping: {operator.value}")

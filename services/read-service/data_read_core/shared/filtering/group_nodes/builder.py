from typing import Any

from ..abstraction import TreeNode
from ..entities import GroupOperator
from ..exceptions import InvalidGroupChildrenError, InvalidGroupingError
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

    def validate(self, raw: dict[str, Any], path: str = "filter_body") -> None:
        present = [group for group in self._known_groups if group.operator.value in raw]
        if len(present) != 1 or len(raw) != 1:
            raise InvalidGroupingError(
                "A group carries exactly one of `and` / `or` and nothing else",
                path=path,
            )

    def parse_raw(
        self,
        raw: dict[str, Any],
        path: str = "filter_body",
    ) -> tuple[GroupOperator, list[dict[str, Any]]]:
        operator_key = next(iter(raw))
        children = raw[operator_key]
        if not isinstance(children, list) or not children:
            raise InvalidGroupChildrenError(
                "A group's children must be a non-empty array",
                path=f"{path}.{operator_key}",
            )

        return GroupOperator(operator_key), children

    def get_related_group(
        self,
        children: list[TreeNode],
        operator: GroupOperator,
        path: str = "filter_body",
    ) -> GroupTreeNode:
        for group in self._known_groups:
            if group.is_related(operator):
                return group(children)

        raise InvalidGroupingError(
            f"Unknown filter grouping: {operator.value}",
            path=path,
        )

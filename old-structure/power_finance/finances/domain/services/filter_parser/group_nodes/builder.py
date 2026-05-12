from typing import Any

from ..abstraction import TreeNode
from .abstraction import GroupTreeNode, FilterGroupTreeNode, GroupNodeBuilder
from .and_group import AndGroupTreeNode, FilterAndGroupTreeNode
from .or_group import OrGroupTreeNode, FilterOrGroupTreeNode
from ....entities import GroupOperator
from ....exceptions import InvalidGroupingError


class StandardGroupNodeBuilder(GroupNodeBuilder):
    _known_groups: list[type[GroupTreeNode]] = [
        AndGroupTreeNode,
        OrGroupTreeNode,
    ]

    def get_related_group(
            self,
            children: list[TreeNode],
            operator: GroupOperator,
    ) -> GroupTreeNode:
        for group in self._known_groups:
            if group.is_related(operator.value):
                return group(children)

        raise InvalidGroupingError(f"Unknown filter grouping: {operator.value}")

    def validate(self, raw: dict[str, Any]) -> bool:
        is_of_type_array: list[bool] = [
            (group.operator.value in raw) for group in self._known_groups
        ]
        is_only_one: bool = is_of_type_array.count(True) == 1

        if not is_only_one:
            raise InvalidGroupingError(f"Filter grouping is breaking one or more constraints")
        return True

    def is_group(self, raw: dict[str, Any]) -> bool:
        for group in self._known_groups:
            if group.operator.value in raw:
                return True

        return False

    def parse_raw(
            self,
            raw_value: dict[str, Any]
    ) -> tuple[GroupOperator, list[dict[str, Any]]]:
        filter_fields: list[dict] = list(raw_value.values())
        operator: str = list(raw_value.keys()).pop(0)

        return (
            GroupOperator(operator),
            [filtered_field for subtree in filter_fields for filtered_field in subtree]
        )


class FilterGroupNodeBuilder(GroupNodeBuilder):
    _known_groups: list[type[FilterGroupTreeNode]] = [
        FilterAndGroupTreeNode,
        FilterOrGroupTreeNode,
    ]

    def get_related_group(
            self,
            children: list[TreeNode],
            operator: GroupOperator
    ) -> FilterGroupTreeNode:
        for group in self._known_groups:
            if group.is_related(operator.value):
                return group(children)

        raise InvalidGroupingError(f"Unknown filter grouping: {operator.value}")

    def validate(self, raw: dict[str, Any]) -> bool:
        is_of_type_array: list[bool] = [
            (group.operator.value in raw) for group in self._known_groups
        ]
        is_only_one: bool = is_of_type_array.count(True) == 1

        if not is_only_one:
            raise InvalidGroupingError(f"Filter grouping is breaking one or more constraints")
        return True

    def is_group(self, raw: dict[str, Any]) -> bool:
        for group in self._known_groups:
            if group.operator.value in raw:
                return True

        return False

    def parse_raw(
            self,
            raw_value: dict[str, Any]
    ) -> tuple[GroupOperator, list[dict[str, Any]]]:
        filter_fields: list[dict] = list(raw_value.values())
        operator: str = list(raw_value.keys()).pop(0)

        return (
            GroupOperator(operator),
            [filtered_field for subtree in filter_fields for filtered_field in subtree]
        )
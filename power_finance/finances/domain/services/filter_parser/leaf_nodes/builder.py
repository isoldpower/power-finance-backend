from typing import Any

from .abstraction import LeafTreeNode, LeafNodeBuilder, FilterLeafTreeNode
from .less_leaf import LessLeafTreeNode, FilterLessLeafTreeNode
from .equal_leaf import EqualLeafTreeNode, FilterEqualLeafTreeNode
from .not_equal_leaf import NotEqualLeafTreeNode, FilterNotEqualLeafTreeNode
from .i_contains_leaf import IContainsLeafTreeNode, FilterIContainsLeafTreeNode
from .contains_leaf import ContainsLeafTreeNode, FilterContainsLeafTreeNode
from .greater_equal_leaf import GreaterEqualLeafTreeNode, FilterGreaterEqualLeafTreeNode
from .less_equal_leaf import LessEqualLeafTreeNode, FilterLessEqualLeafTreeNode
from .greater_leaf import GreaterLeafTreeNode, FilterGreaterLeafTreeNode
from .in_leaf import InLeafTreeNode, FilterInLeafTreeNode
from ....entities import FieldFilter, FilterPolicy
from ....exceptions import InvalidOperationError, PolicyViolationError


class StandardLeafTreeNodeBuilder(LeafNodeBuilder):
    _known_leafs: list[type[LeafTreeNode]] = [
        LessLeafTreeNode,
        EqualLeafTreeNode,
        NotEqualLeafTreeNode,
        IContainsLeafTreeNode,
        ContainsLeafTreeNode,
        GreaterEqualLeafTreeNode,
        LessEqualLeafTreeNode,
        GreaterLeafTreeNode,
        InLeafTreeNode,
    ]

    def get_related_leaf(self, value: FieldFilter) -> LeafTreeNode:
        for leaf_type in StandardLeafTreeNodeBuilder._known_leafs:
            if leaf_type.is_related(value):
                return leaf_type(value)

        raise InvalidOperationError(f"Unknown leaf type: {value}")

    def is_leaf(self, raw_value: dict[str, Any]) -> bool:
        return "field_name" in raw_value and "value" in raw_value and "operator" in raw_value


class FilterLeafNodeBuilder(LeafNodeBuilder):
    _policy: FilterPolicy
    _known_leafs: list[type[FilterLeafTreeNode]] = [
        FilterLessLeafTreeNode,
        FilterEqualLeafTreeNode,
        FilterNotEqualLeafTreeNode,
        FilterIContainsLeafTreeNode,
        FilterContainsLeafTreeNode,
        FilterGreaterEqualLeafTreeNode,
        FilterLessEqualLeafTreeNode,
        FilterGreaterLeafTreeNode,
        FilterInLeafTreeNode,
    ]

    def __init__(self, policy: FilterPolicy):
        self._policy = policy

    def _check_valid_type(self, value: str, referenced_type: type) -> bool:
        try:
            referenced_type(value)
            return True
        except Exception:
            return False

    def get_related_leaf(self, value: FieldFilter) -> FilterLeafTreeNode:
        for leaf_type in self._known_leafs:
            if leaf_type.is_related(value):
                related_policy = self._policy.get(value.field_name)

                return leaf_type(value, related_policy)

        raise InvalidOperationError(f"Unknown leaf type: {value}")

    def is_leaf(self, raw_value: dict[str, Any]) -> bool:
        valid_structure: bool = "field_name" in raw_value and "value" in raw_value and "operator" in raw_value
        if not valid_structure:
            return False

        field_name: str = raw_value.get("field_name")
        operator: str = raw_value.get("operator")
        value: str = raw_value.get("value")

        related_policy = self._policy.get(field_name)
        if not related_policy:
            raise PolicyViolationError(f"No policy specified for field: {field_name}. "
                                       f"Supported fields: {list(self._policy.keys())}")

        valid_operator: bool = operator in related_policy.allowed_operators
        if not valid_operator:
            raise InvalidOperationError(f"Unknown operator type: {operator}. "
                                        f"Allowed operators: {related_policy.allowed_operators}")

        valid_value: bool = self._check_valid_type(value, related_policy.value_type)
        if not valid_value:
            raise InvalidOperationError(f"Unknown value type: {value}. "
                                        f"Specified value type: {related_policy.value_type}")

        return valid_value and valid_operator

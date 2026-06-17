from typing import Any

from ..entities import FieldFilter, FilterPolicy
from ..exceptions import InvalidOperationError, PolicyViolationError
from .abstraction import LeafNodeBuilder, LeafTreeNode
from .equality import EqualLeafTreeNode, NotEqualLeafTreeNode
from .membership import InLeafTreeNode
from .range import (
    GreaterEqualLeafTreeNode,
    GreaterLeafTreeNode,
    LessEqualLeafTreeNode,
    LessLeafTreeNode,
)
from .wildcard import ContainsLeafTreeNode, IContainsLeafTreeNode


class FilterLeafNodeBuilder(LeafNodeBuilder):
    _known_leaves: tuple[type[LeafTreeNode], ...] = (
        EqualLeafTreeNode,
        NotEqualLeafTreeNode,
        IContainsLeafTreeNode,
        ContainsLeafTreeNode,
        GreaterEqualLeafTreeNode,
        LessEqualLeafTreeNode,
        GreaterLeafTreeNode,
        LessLeafTreeNode,
        InLeafTreeNode,
    )

    def __init__(self, policy: FilterPolicy) -> None:
        self._policy = policy

    def is_leaf(self, raw: dict[str, Any]) -> bool:
        if not ("field_name" in raw and "value" in raw and "operator" in raw):
            return False

        return self._policy_for(raw["field_name"]).check_valid_value(raw)

    def get_related_leaf(self, field_filter: FieldFilter) -> LeafTreeNode:
        policy = self._policy_for(field_filter.field_name)
        for leaf_type in self._known_leaves:
            if leaf_type.is_related(field_filter):
                return leaf_type(field_filter, policy)

        raise InvalidOperationError(f"Unknown leaf type: {field_filter}")

    def _policy_for(self, field_name: str):
        policy = self._policy.get(field_name)
        if policy is None:
            raise PolicyViolationError(
                f"No policy specified for field: {field_name}. "
                f"Supported fields: {list(self._policy.keys())}"
            )

        return policy

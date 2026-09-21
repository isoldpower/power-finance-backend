from typing import Any

from filter_grammar_py import (
    ROOT_PATH,
    FieldFilter,
    FilterPolicy,
    PolicyViolationError,
    UnknownNodeError,
)

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

    def is_leaf(
        self,
        raw: dict[str, Any],
        path: str = ROOT_PATH,
    ) -> bool:
        if not ("field_name" in raw and "value" in raw and "operator" in raw):
            return False

        return self._policy_for(raw["field_name"], path).check_valid_value(raw, path)

    def get_related_leaf(
        self,
        field_filter: FieldFilter,
        path: str = ROOT_PATH,
    ) -> LeafTreeNode:
        policy = self._policy_for(field_filter.field_name, path)
        for leaf_type in self._known_leaves:
            if leaf_type.is_related(field_filter):
                return leaf_type(field_filter, policy)

        raise UnknownNodeError(f"Unsupported leaf: {field_filter}", path=path)

    def _policy_for(
        self,
        field_name: str,
        path: str = ROOT_PATH,
    ):
        policy = self._policy.get(field_name)
        if policy is None:
            raise PolicyViolationError(
                f"Field {field_name!r} is not filterable on this resource. "
                f"Filterable fields: {sorted(self._policy)}",
                path=f"{path}.field_name",
            )

        return policy

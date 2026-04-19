from functools import reduce
from operator import or_

from django.db.models import Q

from .abstraction import GroupTreeNode, FilterGroupTreeNode
from ....entities import GroupOperator
from ....exceptions import InvalidStructureError


class OrGroupTreeNode(GroupTreeNode):
    operator: GroupOperator = GroupOperator.Or

    @classmethod
    def is_related(cls, operator: str) -> bool:
        return operator == OrGroupTreeNode.operator.value

    def resolve(self) -> Q:
        resolved_children = [child.resolve() for child in self.children]
        if not resolved_children or len(resolved_children) == 0:
            raise InvalidStructureError("Filtering group must have non-empty list of conditions as value")

        return reduce(or_, resolved_children)

    def resolve_sql(self) -> tuple[str, dict]:
        results = [child.resolve_sql() for child in self.children]
        if not results:
            raise InvalidStructureError("Filtering group must have non-empty list of conditions as value")

        parts, params = zip(*results)
        merged = {}
        for p in params:
            merged.update(p)
        return "(" + " OR ".join(parts) + ")", merged


class FilterOrGroupTreeNode(FilterGroupTreeNode):
    operator: GroupOperator = GroupOperator.Or

    @classmethod
    def is_related(cls, operator: str) -> bool:
        return operator == FilterOrGroupTreeNode.operator.value

    def resolve(self) -> Q:
        resolved_children = [child.resolve() for child in self.children]
        if not resolved_children or len(resolved_children) == 0:
            raise InvalidStructureError("Filtering group must have non-empty list of conditions as value")

        return reduce(or_, resolved_children)

    def resolve_sql(self) -> tuple[str, dict]:
        results = [child.resolve_sql() for child in self.children]
        if not results:
            raise InvalidStructureError("Filtering group must have non-empty list of conditions as value")

        parts, params = zip(*results)
        merged = {}
        for p in params:
            merged.update(p)
        return "(" + " OR ".join(parts) + ")", merged

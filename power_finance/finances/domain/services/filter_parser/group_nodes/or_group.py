from functools import reduce
from operator import or_

from django.db.models import Q

from ....entities import GroupOperator
from ..exceptions import InvalidStructureError
from .abstraction import GroupTreeNode, FilterGroupTreeNode


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

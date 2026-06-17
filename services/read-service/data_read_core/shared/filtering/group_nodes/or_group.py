from functools import reduce
from operator import or_
from typing import Any

from django.db.models import Q

from ..entities import GroupOperator
from .abstraction import GroupTreeNode


class OrGroupTreeNode(GroupTreeNode):
    operator = GroupOperator.Or

    def resolve(self) -> Q:
        return reduce(or_, (child.resolve() for child in self._children))

    def resolve_es(self) -> dict[str, Any]:
        return {
            "bool": {
                "should": [child.resolve_es() for child in self._children],
                "minimum_should_match": 1,
            }
        }

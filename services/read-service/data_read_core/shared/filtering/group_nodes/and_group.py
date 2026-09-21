from functools import reduce
from operator import and_
from typing import Any

from django.db.models import Q
from filter_grammar_py import GroupOperator

from .abstraction import GroupTreeNode


class AndGroupTreeNode(GroupTreeNode):
    operator = GroupOperator.And

    def resolve(self) -> Q:
        return reduce(and_, (child.resolve() for child in self._children))

    def resolve_es(self) -> dict[str, Any]:
        return {"bool": {"must": [child.resolve_es() for child in self._children]}}

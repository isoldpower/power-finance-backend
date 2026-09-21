from typing import Any

from django.db.models import Q
from filter_grammar_py import ComparisonOperator

from .abstraction import LeafTreeNode


class EqualLeafTreeNode(LeafTreeNode):
    operator = ComparisonOperator.Equal

    def resolve(self) -> Q:
        return Q(**{self.model_lookup: self.value})

    def resolve_es(self) -> dict[str, Any]:
        return {"term": {self.es_field: self.value}}


class NotEqualLeafTreeNode(LeafTreeNode):
    operator = ComparisonOperator.NotEqual

    def resolve(self) -> Q:
        return ~Q(**{self.model_lookup: self.value})

    def resolve_es(self) -> dict[str, Any]:
        return {"bool": {"must_not": [{"term": {self.es_field: self.value}}]}}

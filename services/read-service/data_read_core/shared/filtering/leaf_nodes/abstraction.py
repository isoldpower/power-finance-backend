from abc import ABC, abstractmethod
from typing import Any, ClassVar

from django.db.models import Q
from filter_grammar_py import ComparisonOperator, FieldFilter, FilterFieldPolicy

from ..abstraction import TreeNode


class LeafTreeNode(TreeNode):
    operator: ClassVar[ComparisonOperator]

    def __init__(self, field_filter: FieldFilter, policy: FilterFieldPolicy) -> None:
        self._field_filter = field_filter
        self._policy = policy

    @classmethod
    def is_related(cls, field_filter: FieldFilter) -> bool:
        return field_filter.operator is cls.operator

    @property
    def value(self) -> Any:
        return self._field_filter.value

    @property
    def model_lookup(self) -> str:
        return self._policy.model_lookup or self._policy.request_name

    @property
    def es_field(self) -> str:
        return self._policy.es_field or self._policy.request_name


class RangeLeafTreeNode(LeafTreeNode):
    query_suffix: ClassVar[str]
    es_operator: ClassVar[str]

    def resolve(self) -> Q:
        return Q(**{f"{self.model_lookup}__{self.query_suffix}": self.value})

    def resolve_es(self) -> dict[str, Any]:
        return {"range": {self.es_field: {self.es_operator: self.value}}}


class WildcardLeafTreeNode(LeafTreeNode):
    query_suffix: ClassVar[str]
    case_insensitive: ClassVar[bool]

    def resolve(self) -> Q:
        return Q(**{f"{self.model_lookup}__{self.query_suffix}": self.value})

    def resolve_es(self) -> dict[str, Any]:
        return {
            "wildcard": {
                self.es_field: {
                    "value": f"*{escape_wildcard(str(self.value))}*",
                    "case_insensitive": self.case_insensitive,
                }
            }
        }


class LeafNodeBuilder(ABC):
    @abstractmethod
    def is_leaf(self, raw: dict[str, Any], path: str) -> bool: ...

    @abstractmethod
    def get_related_leaf(self, field_filter: FieldFilter, path: str) -> LeafTreeNode: ...


def escape_wildcard(value: str) -> str:
    return value.replace("\\", "\\\\").replace("*", "\\*").replace("?", "\\?")

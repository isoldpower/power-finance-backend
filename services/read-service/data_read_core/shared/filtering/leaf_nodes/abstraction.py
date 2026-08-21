from abc import ABC, abstractmethod
from typing import Any, ClassVar

from django.db.models import Q

from ..abstraction import TreeNode
from ..entities import ComparisonOperator, FieldFilter, FilterFieldPolicy


class LeafTreeNode(TreeNode):
    """A single field comparison. Each concrete subclass binds one
    ComparisonOperator and knows how to render it for the ORM and for ES."""

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
    """Shared rendering for the ordering operators (gt/gte/lt/lte)."""

    query_suffix: ClassVar[str]
    es_operator: ClassVar[str]

    def resolve(self) -> Q:
        return Q(**{f"{self.model_lookup}__{self.query_suffix}": self.value})

    def resolve_es(self) -> dict[str, Any]:
        return {"range": {self.es_field: {self.es_operator: self.value}}}


class WildcardLeafTreeNode(LeafTreeNode):
    """Shared rendering for substring operators (contains/icontains)."""

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

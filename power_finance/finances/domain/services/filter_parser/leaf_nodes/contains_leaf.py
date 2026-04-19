import uuid

from django.db.models import Q

from .abstraction import LeafTreeNode, FilterLeafTreeNode
from ....entities import FieldFilter, ComparisonOperator
from ....exceptions import PolicyViolationError


def _like_pattern(value: str) -> str:
    escaped = value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    return f"%{escaped}%"


def _contains_sql(column: str, value: str) -> tuple[str, dict]:
    pname = f"p{uuid.uuid4().hex[:8]}"
    return f"{column} LIKE @{pname} ESCAPE '\\'", {pname: _like_pattern(value)}


class ContainsLeafTreeNode(LeafTreeNode):
    @classmethod
    def is_related(cls, value: FieldFilter) -> bool:
        return value.operator.value == ComparisonOperator.Contains.value

    def resolve(self) -> Q:
        return Q(**{f"{self.field_name}__contains": self.value})

    def resolve_sql(self) -> tuple[str, dict]:
        return _contains_sql(self.field_name, self.value)


class FilterContainsLeafTreeNode(FilterLeafTreeNode):
    @classmethod
    def is_related(cls, value: FieldFilter) -> bool:
        return value.operator.value == ComparisonOperator.Contains.value

    def resolve(self) -> Q:
        if self.operator.value in self.policy.allowed_operators:
            return Q(**{f"{self.policy.model_lookup}__contains": self.value})

        raise PolicyViolationError(f"Filter {self.operator} is forbidden for {self.policy.request_name} field")

    def resolve_sql(self) -> tuple[str, dict]:
        if self.operator.value in self.policy.allowed_operators:
            return _contains_sql(self.policy.model_lookup, self.value)

        raise PolicyViolationError(f"Filter {self.operator} is forbidden for {self.policy.request_name} field")

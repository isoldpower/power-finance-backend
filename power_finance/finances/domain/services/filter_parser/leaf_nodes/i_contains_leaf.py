import uuid

from django.db.models import Q

from .abstraction import LeafTreeNode, FilterLeafTreeNode
from ....exceptions import PolicyViolationError
from ....entities import FieldFilter, ComparisonOperator


def _icontains_sql(column: str, value: str) -> tuple[str, dict]:
    escaped = value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    pname = f"p{uuid.uuid4().hex[:8]}"
    return f"LOWER({column}) LIKE LOWER(@{pname}) ESCAPE '\\'", {pname: f"%{escaped}%"}


class IContainsLeafTreeNode(LeafTreeNode):
    @classmethod
    def is_related(cls, value: FieldFilter) -> bool:
        return value.operator.value == ComparisonOperator.IContains.value

    def resolve(self) -> Q:
        return Q(**{f"{self.field_name}__icontains": self.value})

    def resolve_sql(self) -> tuple[str, dict]:
        return _icontains_sql(self.field_name, self.value)


class FilterIContainsLeafTreeNode(FilterLeafTreeNode):
    @classmethod
    def is_related(cls, value: FieldFilter) -> bool:
        return value.operator.value == ComparisonOperator.IContains.value

    def resolve(self) -> Q:
        if self.operator.value in self.policy.allowed_operators:
            return Q(**{f"{self.policy.model_lookup}__icontains": self.value})

        raise PolicyViolationError(f"Filter {self.operator} is forbidden for {self.policy.request_name} field")

    def resolve_sql(self) -> tuple[str, dict]:
        if self.operator.value in self.policy.allowed_operators:
            return _icontains_sql(self.policy.model_lookup, self.value)

        raise PolicyViolationError(f"Filter {self.operator} is forbidden for {self.policy.request_name} field")

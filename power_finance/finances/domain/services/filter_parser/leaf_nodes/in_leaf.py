import uuid

from django.db.models import Q

from .abstraction import LeafTreeNode, FilterLeafTreeNode
from ....exceptions import PolicyViolationError
from ....entities import FieldFilter, ComparisonOperator


class InLeafTreeNode(LeafTreeNode):
    @classmethod
    def is_related(cls, value: FieldFilter) -> bool:
        return value.operator.value == ComparisonOperator.In.value

    def resolve(self) -> Q:
        return Q(**{f"{self.field_name}__in": self.value})

    def resolve_sql(self) -> tuple[str, dict]:
        pnames = [f"p{uuid.uuid4().hex[:8]}" for _ in self.value]
        placeholders = ", ".join(f"@{n}" for n in pnames)
        params = dict(zip(pnames, self.value))
        return f"{self.field_name} IN ({placeholders})", params


class FilterInLeafTreeNode(FilterLeafTreeNode):
    @classmethod
    def is_related(cls, value: FieldFilter) -> bool:
        return value.operator.value == ComparisonOperator.In.value

    def resolve(self) -> Q:
        if self.operator.value in self.policy.allowed_operators:
            return Q(**{f"{self.policy.model_lookup}__in": self.value})

        raise PolicyViolationError(f"Filter {self.operator} is forbidden for {self.policy.request_name} field")

    def resolve_sql(self) -> tuple[str, dict]:
        if self.operator.value in self.policy.allowed_operators:
            pnames = [f"p{uuid.uuid4().hex[:8]}" for _ in self.value]
            placeholders = ", ".join(f"@{n}" for n in pnames)
            params = dict(zip(pnames, self.value))
            return f"{self.policy.model_lookup} IN ({placeholders})", params

        raise PolicyViolationError(f"Filter {self.operator} is forbidden for {self.policy.request_name} field")

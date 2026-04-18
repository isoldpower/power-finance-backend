from django.db.models import Q

from .abstraction import LeafTreeNode, FilterLeafTreeNode
from ....exceptions import PolicyViolationError
from ....entities import FieldFilter, ComparisonOperator


class GreaterLeafTreeNode(LeafTreeNode):
    @classmethod
    def is_related(cls, value: FieldFilter) -> bool:
        return value.operator.value == ComparisonOperator.Greater.value

    def resolve(self) -> Q:
        return Q(**{f"{self.field_name}__gt": self.value})

    def resolve_sql(self) -> str:
        return f"{self.field_name} > '{self.value}'"


class FilterGreaterLeafTreeNode(FilterLeafTreeNode):
    @classmethod
    def is_related(cls, value: FieldFilter) -> bool:
        return value.operator.value == ComparisonOperator.Greater.value

    def resolve(self) -> Q:
        if self.operator.value in self.policy.allowed_operators:
            return Q(**{f"{self.policy.model_lookup}__gt": self.value})

        raise PolicyViolationError(f"Filter {self.operator} is forbidden for {self.policy.request_name} field")

    def resolve_sql(self) -> str:
        if self.operator.value in self.policy.allowed_operators:
            return f"{self.policy.model_lookup} > '{self.value}'"

        raise PolicyViolationError(f"Filter {self.operator} is forbidden for {self.policy.request_name} field")

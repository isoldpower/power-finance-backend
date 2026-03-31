from django.db.models import Q

from .abstraction import LeafTreeNode, FilterLeafTreeNode
from ....entities import FieldFilter, ComparisonOperator
from ....exceptions import PolicyViolationError


class ContainsLeafTreeNode(LeafTreeNode):
    @classmethod
    def is_related(cls, value: FieldFilter) -> bool:
        return value.operator.value == ComparisonOperator.Contains.value

    def resolve(self) -> Q:
        return Q(**{f"{self.field_name}__contains": self.value})


class FilterContainsLeafTreeNode(FilterLeafTreeNode):
    @classmethod
    def is_related(cls, value: FieldFilter) -> bool:
        return value.operator.value == ComparisonOperator.Contains.value

    def resolve(self) -> Q:
        if self.operator.value in self.policy.allowed_operators:
            return Q(**{f"{self.policy.model_lookup}__contains": self.value})

        raise PolicyViolationError(f"Filter {self.operator} is forbidden for {self.policy.request_name} field")

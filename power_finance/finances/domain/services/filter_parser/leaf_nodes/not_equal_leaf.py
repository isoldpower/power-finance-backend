from django.db.models import Q

from ....entities import FieldFilter, ComparisonOperator
from ..exceptions import PolicyViolationError
from .abstraction import LeafTreeNode, FilterLeafTreeNode


class NotEqualLeafTreeNode(LeafTreeNode):
    @classmethod
    def is_related(cls, value: FieldFilter) -> bool:
        return value.operator.value == ComparisonOperator.NotEqual.value

    def resolve(self) -> Q:
        return ~Q(**{self.field_name: self.value})


class FilterNotEqualLeafTreeNode(FilterLeafTreeNode):
    @classmethod
    def is_related(cls, value: FieldFilter) -> bool:
        return value.operator.value == ComparisonOperator.NotEqual.value

    def resolve(self) -> Q:
        if self.operator.value in self.policy.allowed_operators:
            return ~Q(**{self.policy.model_lookup: self.value})

        raise PolicyViolationError(f"Filter {self.operator} is forbidden for {self.policy.request_name} field")

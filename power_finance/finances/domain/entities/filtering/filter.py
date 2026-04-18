from enum import Enum
from dataclasses import dataclass
from typing import Union, Any

from django.db.models import Q

from .type_validation import TypeValidatorBuilder, TypeVariant
from ...exceptions import InvalidOperationError


class ComparisonOperator(str, Enum):
    Equal = "eq"
    NotEqual = "neq"
    IContains = "icontains"
    Contains = "contains"
    GreaterEqual = "gte"
    LessEqual = "lte"
    Greater = "gt"
    Less = "lt"
    In = "in"


class GroupOperator(str, Enum):
    And = "and"
    Or = "or"


@dataclass(frozen=True)
class FieldFilter:
    field_name: str
    operator: ComparisonOperator
    value: str


@dataclass(frozen=True)
class FilterGroup:
    operator: GroupOperator
    fields: list[Union[FieldFilter, 'FilterGroup']]


@dataclass(frozen=True)
class FilterFieldPolicy:
    request_name: str
    model_lookup: str
    allowed_operators: set[str]
    value_type: TypeVariant

    def check_valid_value(self, raw_value: dict[str, Any]) -> bool:
        operator = raw_value.get("operator")
        valid_operator: bool = operator and operator in self.allowed_operators
        if not valid_operator:
            raise InvalidOperationError(f"Unknown operator type: {operator}. "
                                        f"Allowed operators: {self.allowed_operators}")

        value = raw_value.get("value")
        type_validator = TypeValidatorBuilder.build_validator(self.value_type, value)
        valid_value: bool = value and type_validator.validate()
        if not valid_value:
            raise InvalidOperationError(f"Unknown value type: {value}. "
                                        f"Specified value type: {self.value_type}")

        return valid_value and valid_operator


FilterPolicy = dict[str, FilterFieldPolicy]


@dataclass(frozen=True)
class ResolvedFilterTree:
    django_query: Q
    raw_sql_query: str
    applied_policy: FilterPolicy

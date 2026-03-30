from enum import Enum
from dataclasses import dataclass
from typing import Union

from django.db.models import Q


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
    fields: list[FilterNode]


@dataclass(frozen=True)
class FilterFieldPolicy:
    request_name: str
    model_lookup: str
    allowed_operators: set[str]
    value_type: type


@dataclass(frozen=True)
class ResolvedFilterTree:
    query: Q
    applied_policy: FilterPolicy


FilterPolicy = dict[str, FilterFieldPolicy]
FilterNode = Union[FieldFilter, FilterGroup]

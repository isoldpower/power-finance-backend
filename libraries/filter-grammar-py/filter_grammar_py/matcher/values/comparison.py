from typing import Any

from ...entities import FilterFieldPolicy
from ...value_types import value_type_for
from ...vocabulary import ComparisonOperator
from .membership import contains
from .operators import OPERATORS


def compare(
    operator: str,
    present: Any,
    expected: Any,
    field_policy: FilterFieldPolicy,
) -> bool:
    value_type = value_type_for(field_policy.value_type)
    left = value_type.coerce(present)

    if operator == ComparisonOperator.In:
        return contains(left, expected, value_type)

    return OPERATORS[operator](left, value_type.coerce(expected))

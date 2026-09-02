from dataclasses import dataclass
from typing import Any

from .exceptions import InvalidOperationError, InvalidValueError
from .value_types import value_type_for
from .vocabulary import ComparisonOperator, GroupOperator, TypeVariant

__all__ = [
    "ComparisonOperator",
    "FieldFilter",
    "FilterFieldPolicy",
    "FilterPolicy",
    "GroupOperator",
    "TypeVariant",
]


@dataclass(frozen=True)
class FieldFilter:
    field_name: str
    operator: ComparisonOperator
    value: Any


@dataclass(frozen=True)
class FilterFieldPolicy:
    request_name: str
    allowed_operators: set[str]
    value_type: TypeVariant
    model_lookup: str = ""
    es_field: str = ""

    def check_valid_value(
        self,
        raw_value: dict[str, Any],
        path: str = "filter_body",
    ) -> bool:
        operator = raw_value.get("operator")
        if not operator or operator not in self.allowed_operators:
            raise InvalidOperationError(
                f"Operator {operator!r} is not permitted on {self.request_name!r}. "
                f"Allowed operators: {sorted(self.allowed_operators)}",
                path=f"{path}.operator",
            )

        value = raw_value.get("value")
        if value is None or not value_type_for(self.value_type).accepts_all(value):
            raise InvalidValueError(
                f"Value does not match the {self.value_type} type of {self.request_name!r}",
                path=f"{path}.value",
            )

        return True


FilterPolicy = dict[str, FilterFieldPolicy]

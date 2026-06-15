import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from .exceptions import InvalidOperationError


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


class TypeVariant(str, Enum):
    INTEGER = "int"
    FLOAT = "float"
    STRING = "str"
    BOOLEAN = "bool"
    DATETIME = "datetime"
    UUID = "uuid"


_TYPE_VALIDATORS = {
    TypeVariant.INTEGER: lambda value: bool(re.fullmatch(r"^[+-]?\d+$", str(value))),
    TypeVariant.FLOAT: lambda value: bool(re.fullmatch(r"^[+-]?(\d+\.\d+|\d+|\.\d+)$", str(value))),
    TypeVariant.STRING: lambda value: True,
    TypeVariant.BOOLEAN: lambda value: isinstance(value, bool)
    or bool(re.fullmatch(r"^(true|false|1|0)$", str(value), re.IGNORECASE)),
    TypeVariant.DATETIME: lambda value: _is_iso_datetime(value),
    TypeVariant.UUID: lambda value: _is_uuid(value),
}


def _is_iso_datetime(value: Any) -> bool:
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def _is_uuid(value: Any) -> bool:
    try:
        UUID(str(value))
        return True
    except ValueError:
        return False


@dataclass(frozen=True)
class FieldFilter:
    field_name: str
    operator: ComparisonOperator
    value: Any


@dataclass(frozen=True)
class FilterFieldPolicy:
    """Per-field whitelist: which operators a client may use on the field,
    what value type it carries, and how the request name maps to the store
    (Django ORM lookup and/or Elasticsearch field)."""

    request_name: str
    allowed_operators: set[str]
    value_type: TypeVariant
    model_lookup: str = ""
    es_field: str = ""

    def check_valid_value(self, raw_value: dict[str, Any]) -> bool:
        operator = raw_value.get("operator")
        if not operator or operator not in self.allowed_operators:
            raise InvalidOperationError(
                f"Unknown operator type: {operator}. "
                f"Allowed operators: {self.allowed_operators}"
            )

        value = raw_value.get("value")
        if value is None or not self._validate_value(value):
            raise InvalidOperationError(
                f"Unknown value type: {value}. Specified value type: {self.value_type}"
            )

        return True

    def _validate_value(self, value: Any) -> bool:
        if isinstance(value, list):
            return all(_TYPE_VALIDATORS[self.value_type](item) for item in value)
        return _TYPE_VALIDATORS[self.value_type](value)


FilterPolicy = dict[str, FilterFieldPolicy]

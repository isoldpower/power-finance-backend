from typing import Any

from ...value_types import UncomparableValue, ValueType
from .sentinels import NEVER_EQUAL


def contains(left: Any, expected: Any, value_type: ValueType) -> bool:
    match expected:
        case [*candidates]:
            return any(left == _lenient(value_type, candidate) for candidate in candidates)
        case _:
            raise UncomparableValue()


def _lenient(value_type: ValueType, value: Any) -> Any:
    try:
        return value_type.coerce(value)
    except UncomparableValue:
        return NEVER_EQUAL

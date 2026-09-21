import re
from typing import Any

from ..vocabulary import TypeVariant
from .base import ValueType
from .exceptions import UncomparableValue

FLOAT_LITERAL = re.compile(r"^[+-]?(\d+\.\d+|\d+|\.\d+)$")


class FloatType(ValueType):
    variant = TypeVariant.FLOAT

    def accepts(self, value: Any) -> bool:
        return bool(FLOAT_LITERAL.fullmatch(str(value)))

    def coerce(self, value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError) as failure:
            raise UncomparableValue() from failure

import re
from typing import Any

from ..vocabulary import TypeVariant
from .base import ValueType
from .exceptions import UncomparableValue

INTEGER_LITERAL = re.compile(r"^[+-]?\d+$")


class IntegerType(ValueType):
    variant = TypeVariant.INTEGER

    def accepts(self, value: Any) -> bool:
        return bool(INTEGER_LITERAL.fullmatch(str(value)))

    def coerce(self, value: Any) -> int:
        try:
            return int(str(value))
        except ValueError as failure:
            raise UncomparableValue() from failure

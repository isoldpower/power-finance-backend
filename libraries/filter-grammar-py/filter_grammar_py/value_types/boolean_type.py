import re
from typing import Any

from ..vocabulary import TypeVariant
from .base import ValueType
from .exceptions import UncomparableValue

BOOLEAN_LITERAL = re.compile(r"^(true|false|1|0)$", re.IGNORECASE)

TRUTHS = frozenset({"true", "1"})
FALSEHOODS = frozenset({"false", "0"})


class BooleanType(ValueType):
    variant = TypeVariant.BOOLEAN

    def accepts(self, value: Any) -> bool:
        return bool(BOOLEAN_LITERAL.fullmatch(str(value)))

    def coerce(self, value: Any) -> bool:
        lowered = str(value).lower()
        if lowered in TRUTHS:
            return True
        if lowered in FALSEHOODS:
            return False

        raise UncomparableValue()

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from ..vocabulary import TypeVariant
from .base import ValueType
from .exceptions import UncomparableValue

CANONICAL_AMOUNT = re.compile(r"^-?(0|[1-9][0-9]*)(\.[0-9]+)?$")


class DecimalType(ValueType):
    variant = TypeVariant.DECIMAL

    def accepts(self, value: Any) -> bool:
        try:
            return bool(CANONICAL_AMOUNT.fullmatch(value))
        except TypeError:
            return False

    def coerce(self, value: Any) -> Decimal:
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as failure:
            raise UncomparableValue() from failure

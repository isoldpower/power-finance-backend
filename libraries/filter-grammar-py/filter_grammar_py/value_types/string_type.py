from typing import Any

from ..vocabulary import TypeVariant
from .base import ValueType


class StringType(ValueType):
    variant = TypeVariant.STRING

    def accepts(self, value: Any) -> bool:
        return True

    def coerce(self, value: Any) -> str:
        return str(value)

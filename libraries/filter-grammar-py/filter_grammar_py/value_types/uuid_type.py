from typing import Any
from uuid import UUID

from ..vocabulary import TypeVariant
from .base import ValueType
from .exceptions import UncomparableValue


class UuidType(ValueType):
    variant = TypeVariant.UUID

    def accepts(self, value: Any) -> bool:
        try:
            UUID(str(value))

            return True
        except ValueError:
            return False

    def coerce(self, value: Any) -> str:
        try:
            return str(UUID(str(value)))
        except ValueError as failure:
            raise UncomparableValue() from failure

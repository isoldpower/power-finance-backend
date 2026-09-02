from datetime import UTC, datetime
from typing import Any

from ..vocabulary import TypeVariant
from .base import ValueType
from .exceptions import UncomparableValue


class DateTimeType(ValueType):
    variant = TypeVariant.DATETIME

    def accepts(self, value: Any) -> bool:
        try:
            self._parsed(value)

            return True
        except UncomparableValue:
            return False

    def coerce(self, value: Any) -> datetime:
        match value:
            case datetime():
                moment = value
            case _:
                moment = self._parsed(value)

        return moment if moment.tzinfo else moment.replace(tzinfo=UTC)

    def _parsed(self, value: Any) -> datetime:
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError as failure:
            raise UncomparableValue() from failure

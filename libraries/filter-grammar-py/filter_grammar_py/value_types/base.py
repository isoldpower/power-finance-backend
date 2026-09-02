from abc import ABC, abstractmethod
from typing import Any

from ..vocabulary import TypeVariant


class ValueType(ABC):
    variant: TypeVariant

    @abstractmethod
    def accepts(self, value: Any) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def coerce(self, value: Any) -> Any:
        raise NotImplementedError()

    def accepts_all(self, value: Any) -> bool:
        match value:
            case [*items]:
                return all(self.accepts(item) for item in items)
            case _:
                return self.accepts(value)

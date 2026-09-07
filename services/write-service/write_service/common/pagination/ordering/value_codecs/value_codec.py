from abc import ABC, abstractmethod
from typing import Any


class ValueCodec(ABC):
    def to_cursor_value(self, value: Any) -> Any:
        return None if value is None else self._encode(value)

    def from_cursor_value(self, value: Any) -> Any:
        return None if value is None else self._decode(value)

    @abstractmethod
    def _encode(self, value: Any) -> Any:
        raise NotImplementedError()

    @abstractmethod
    def _decode(self, value: Any) -> Any:
        raise NotImplementedError()

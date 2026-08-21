from abc import ABC, abstractmethod
from typing import Any


class ValueCodec(ABC):
    """Translates one sort key's value between the row it was read from, the
    cursor payload it travels in, and the store that has to compare it."""

    def to_cursor_value(self, value: Any) -> Any:
        return None if value is None else self._encode(value)

    def from_cursor_value(self, value: Any) -> Any:
        return None if value is None else self._decode(value)

    def to_elasticsearch_value(self, value: Any) -> Any:
        return None if value is None else self._to_elasticsearch(value)

    @abstractmethod
    def _encode(self, value: Any) -> Any:
        raise NotImplementedError()

    @abstractmethod
    def _decode(self, value: Any) -> Any:
        raise NotImplementedError()

    def _to_elasticsearch(self, value: Any) -> Any:
        return self._decode(value)

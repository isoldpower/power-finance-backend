from dataclasses import dataclass
from typing import Any

from .value_codec import ValueCodec


@dataclass(frozen=True)
class IntegerCodec(ValueCodec):
    def _encode(self, value: Any) -> Any:
        return int(value)

    def _decode(self, value: Any) -> Any:
        return int(value)

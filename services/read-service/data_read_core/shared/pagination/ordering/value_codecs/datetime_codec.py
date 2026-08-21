from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .value_codec import ValueCodec

MILLISECONDS_PER_SECOND = 1000
ZULU_SUFFIX = "Z"
UTC_OFFSET = "+00:00"


@dataclass(frozen=True)
class DateTimeCodec(ValueCodec):
    """Timestamps travel as ISO-8601 text."""

    def _encode(self, value: Any) -> Any:
        return value.isoformat() if isinstance(value, datetime) else str(value)

    def _decode(self, value: Any) -> Any:
        return datetime.fromisoformat(str(value).replace(ZULU_SUFFIX, UTC_OFFSET))

    def _to_elasticsearch(self, value: Any) -> Any:
        return int(self._decode(value).timestamp() * MILLISECONDS_PER_SECOND)

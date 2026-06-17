from dataclasses import dataclass
from datetime import UTC, datetime

from .. import headers as Headers
from ..message import ConsumedMessage


@dataclass(frozen=True, slots=True)
class RetryContext:
    retry_topic_attempts_consumed: int
    first_failed_at: datetime | None

    @classmethod
    def from_message(cls, message: ConsumedMessage) -> "RetryContext":
        return cls(
            retry_topic_attempts_consumed=Headers.get_int(
                message.headers,
                Headers.HEADER_RETRY_COUNT,
                default=0,
            ),
            first_failed_at=Headers.get_datetime(
                message.headers,
                Headers.HEADER_FIRST_FAILED_AT,
            ),
        )

    def first_failed_at_or_now(self) -> datetime:
        return self.first_failed_at or datetime.now(UTC)

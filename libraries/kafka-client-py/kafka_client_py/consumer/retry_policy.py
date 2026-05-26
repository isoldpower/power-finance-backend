import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from ..errors import PoisonError, TransientError


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_in_process_attempts: int = 3
    max_retry_topic_attempts: int = 5

    initial_backoff: timedelta = timedelta(seconds=1)
    max_backoff: timedelta = timedelta(minutes=10)
    backoff_multiplier: float = 2.0
    jitter_ratio: float = 0.2

    retryable: tuple[type[BaseException], ...] = field(default_factory=tuple)

    def is_retryable(self, exception: BaseException) -> bool:
        if isinstance(exception, PoisonError):
            return False
        if isinstance(exception, TransientError):
            return True
        return isinstance(exception, self.retryable)

    def compute_backoff(self, retry_topic_attempt: int) -> timedelta:
        if retry_topic_attempt < 1:
            retry_topic_attempt = 1

        base_seconds = self.initial_backoff.total_seconds() * (
            self.backoff_multiplier ** (retry_topic_attempt - 1)
        )
        capped_seconds = min(base_seconds, self.max_backoff.total_seconds())

        if self.jitter_ratio > 0:
            jitter_spread = capped_seconds * self.jitter_ratio
            capped_seconds = capped_seconds + random.uniform(
                -jitter_spread,
                jitter_spread,
            )
            capped_seconds = max(capped_seconds, 0.0)

        return timedelta(seconds=capped_seconds)

    def compute_retry_at(
        self,
        retry_topic_attempt: int,
        *,
        now: datetime | None = None,
    ) -> datetime:
        base_timestamp = now or datetime.now(UTC)
        return base_timestamp + self.compute_backoff(retry_topic_attempt)

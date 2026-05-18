"""Retry policy: budgets, classification, backoff math.

A `RetryPolicy` describes *what* to do on failure; the handler wrapper executes
the policy. Two budgets are tracked separately because they have different
costs:

* `max_in_process_attempts` — re-runs inside the consumer process. Cheap.
  Useful for sub-second blips (TCP RST, momentary lock wait).
* `max_retry_topic_attempts` — re-publishes to events.retry with a delay.
  Survives consumer restarts, but each attempt costs a topic round-trip.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from .errors import PoisonError, TransientError


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_in_process_attempts: int = 3
    max_retry_topic_attempts: int = 5

    initial_backoff: timedelta = timedelta(seconds=1)
    max_backoff: timedelta = timedelta(minutes=10)
    backoff_multiplier: float = 2.0
    jitter_ratio: float = 0.2  # +/- 20% jitter, full-jitter style

    # Exceptions raised by user code that should be treated as transient.
    # `TransientError` is always transient regardless. `PoisonError` is always poison.
    retryable: tuple[type[BaseException], ...] = field(default_factory=tuple)

    def is_retryable(self, exc: BaseException) -> bool:
        if isinstance(exc, PoisonError):
            return False
        if isinstance(exc, TransientError):
            return True
        return isinstance(exc, self.retryable)

    def compute_backoff(self, retry_topic_attempt: int) -> timedelta:
        """Exponential backoff with bounded jitter.

        `retry_topic_attempt` is 1-indexed: the first retry-topic publish is
        attempt 1, gets `initial_backoff` (jittered).
        """
        if retry_topic_attempt < 1:
            retry_topic_attempt = 1

        base_seconds = self.initial_backoff.total_seconds() * (
            self.backoff_multiplier ** (retry_topic_attempt - 1)
        )
        capped = min(base_seconds, self.max_backoff.total_seconds())

        if self.jitter_ratio > 0:
            spread = capped * self.jitter_ratio
            capped = capped + random.uniform(-spread, spread)
            capped = max(capped, 0.0)

        return timedelta(seconds=capped)

    def compute_retry_at(
        self, retry_topic_attempt: int, *, now: datetime | None = None
    ) -> datetime:
        base = now or datetime.now(UTC)
        return base + self.compute_backoff(retry_topic_attempt)

"""Error taxonomy for the consumer error-routing pipeline.

The handler wrapper inspects raised exceptions to decide between three outcomes:

* `TransientError` — re-runnable. In-process retry, then events.retry, then DLQ.
* `PoisonError` — terminal. Straight to DLQ, no retry. Use for schema /
  validation / permanent business-invariant failures.
* anything else — classified by the user-supplied `retryable` tuple on
  `RetryPolicy`. Unknown exceptions default to *poison* — better to surface
  in DLQ than spin forever on a bug the consumer can't recover from.
"""

from __future__ import annotations


class KafkaHandlerError(Exception):
    """Base for errors raised by this library's wrappers (not by user code)."""


class TransientError(Exception):
    """Re-runnable failure (network blip, DB connection reset, 5xx, timeout)."""


class PoisonError(Exception):
    """Terminal failure (bad payload, schema mismatch, broken invariant).

    Skips retry entirely and routes to DLQ on first occurrence.
    """


class RetryExhaustedError(KafkaHandlerError):
    """Raised internally when both in-process and retry-topic budgets are spent.

    Surfaced for observability; routing to DLQ happens regardless.
    """

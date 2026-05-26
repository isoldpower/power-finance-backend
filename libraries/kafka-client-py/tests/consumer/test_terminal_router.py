"""TerminalRouter: routes a terminally-failed message to retry-topic OR DLQ.

The three branches that matter:
1. route_immediate_failure → always DLQ (poison / non-retryable).
2. route_terminal_failure with retry-topic budget remaining → retry topic.
3. route_terminal_failure with retry-topic budget exhausted → DLQ.

`total_attempts` reported to DLQ must include BOTH retry-topic attempts
already consumed AND the in-process attempts just made — pin this so a
refactor doesn't accidentally double-count or under-count.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from kafka_client_py.consumer.retry_context import RetryContext
from kafka_client_py.consumer.retry_policy import RetryPolicy
from kafka_client_py.consumer.terminal_router import TerminalRouter
from kafka_client_py.publisher.dlq_publisher import DLQPublisher
from kafka_client_py.publisher.retry_publisher import RetryPublisher

from tests.fakes import FakeMessage, FakePublisher


def _wire(policy: RetryPolicy) -> tuple[TerminalRouter, FakePublisher]:
    pub = FakePublisher()
    return (
        TerminalRouter(
            retry_policy=policy,
            retry_publisher=RetryPublisher(pub, topic="events.retry"),  # type: ignore[arg-type]
            dlq_publisher=DLQPublisher(pub, topic="events.dlq"),  # type: ignore[arg-type]
        ),
        pub,
    )


# ---------------------------------------------------------------------------
# route_immediate_failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_immediate_failure_always_goes_to_dlq():
    # Poison / non-retryable: no retry-topic shuffle, straight to DLQ.
    router, pub = _wire(RetryPolicy(max_retry_topic_attempts=10))
    ctx = RetryContext(retry_topic_attempts_consumed=2, first_failed_at=None)

    await router.route_immediate_failure(
        FakeMessage(),
        exception=ValueError("nope"),
        retry_context=ctx,
        in_process_attempts_made=1,
        reason="non_retryable",
    )

    assert len(pub.published) == 1
    assert pub.published[0].topic == "events.dlq"


@pytest.mark.asyncio
async def test_immediate_failure_reports_total_attempts_as_sum():
    # total_attempts = retry-topic attempts so far + in-process attempts.
    router, pub = _wire(RetryPolicy())
    ctx = RetryContext(retry_topic_attempts_consumed=4, first_failed_at=None)

    await router.route_immediate_failure(
        FakeMessage(),
        exception=RuntimeError("boom"),
        retry_context=ctx,
        in_process_attempts_made=3,
        reason="poison",
    )

    from kafka_client_py import headers as H

    pub_out = pub.published[0]
    assert H.get_int(pub_out.headers, H.HEADER_RETRY_COUNT) == 7


# ---------------------------------------------------------------------------
# route_terminal_failure: budget remaining → retry topic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_terminal_failure_with_budget_remaining_goes_to_retry_topic():
    router, pub = _wire(
        RetryPolicy(
            max_retry_topic_attempts=5,
            initial_backoff=timedelta(seconds=0),
            jitter_ratio=0.0,
        )
    )
    ctx = RetryContext(retry_topic_attempts_consumed=2, first_failed_at=None)

    await router.route_terminal_failure(
        FakeMessage(),
        last_exception=ConnectionError("blip"),
        retry_context=ctx,
        in_process_attempts_made=3,
    )

    assert len(pub.published) == 1
    assert pub.published[0].topic == "events.retry"


@pytest.mark.asyncio
async def test_retry_topic_attempt_number_is_incremented_by_one():
    # Republishing onto the retry topic stamps the NEXT attempt number,
    # not the one just consumed.
    router, pub = _wire(
        RetryPolicy(
            max_retry_topic_attempts=5,
            initial_backoff=timedelta(seconds=0),
            jitter_ratio=0.0,
        )
    )
    ctx = RetryContext(retry_topic_attempts_consumed=2, first_failed_at=None)

    await router.route_terminal_failure(
        FakeMessage(),
        last_exception=ConnectionError(),
        retry_context=ctx,
        in_process_attempts_made=1,
    )

    from kafka_client_py import headers as H

    assert H.get_int(pub.published[0].headers, H.HEADER_RETRY_COUNT) == 3


@pytest.mark.asyncio
async def test_retry_topic_message_includes_retry_at_header():
    # Without this, the scheduler can't delay redelivery.
    now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    router, pub = _wire(
        RetryPolicy(
            max_retry_topic_attempts=5,
            initial_backoff=timedelta(seconds=30),
            backoff_multiplier=1.0,
            jitter_ratio=0.0,
        )
    )

    await router.route_terminal_failure(
        FakeMessage(),
        last_exception=ConnectionError(),
        retry_context=RetryContext(retry_topic_attempts_consumed=0, first_failed_at=now),
        in_process_attempts_made=1,
    )

    from kafka_client_py import headers as H

    retry_at = H.get_datetime(pub.published[0].headers, H.HEADER_RETRY_AT)
    assert retry_at is not None
    assert retry_at.tzinfo is not None  # always UTC-aware


# ---------------------------------------------------------------------------
# route_terminal_failure: budget exhausted → DLQ
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_terminal_failure_with_budget_exhausted_goes_to_dlq():
    # consumed == max means no slot left; promote straight to DLQ.
    router, pub = _wire(RetryPolicy(max_retry_topic_attempts=3))
    ctx = RetryContext(retry_topic_attempts_consumed=3, first_failed_at=None)

    await router.route_terminal_failure(
        FakeMessage(),
        last_exception=ConnectionError("dead"),
        retry_context=ctx,
        in_process_attempts_made=2,
    )

    assert len(pub.published) == 1
    assert pub.published[0].topic == "events.dlq"


@pytest.mark.asyncio
async def test_terminal_failure_budget_exceeded_also_goes_to_dlq():
    # Defensive: consumed > max (somehow) must NOT silently re-queue.
    router, pub = _wire(RetryPolicy(max_retry_topic_attempts=3))
    ctx = RetryContext(retry_topic_attempts_consumed=99, first_failed_at=None)

    await router.route_terminal_failure(
        FakeMessage(),
        last_exception=ConnectionError(),
        retry_context=ctx,
        in_process_attempts_made=1,
    )

    assert pub.published[0].topic == "events.dlq"


@pytest.mark.asyncio
async def test_exhausted_to_dlq_reports_combined_total_attempts():
    router, pub = _wire(RetryPolicy(max_retry_topic_attempts=3))
    ctx = RetryContext(retry_topic_attempts_consumed=3, first_failed_at=None)

    await router.route_terminal_failure(
        FakeMessage(),
        last_exception=ConnectionError(),
        retry_context=ctx,
        in_process_attempts_made=2,
    )

    from kafka_client_py import headers as H

    assert H.get_int(pub.published[0].headers, H.HEADER_RETRY_COUNT) == 5

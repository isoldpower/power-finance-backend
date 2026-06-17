"""RetryContext: derives the per-message retry state from headers.

The whole retry/DLQ pipeline reads retry_topic_attempts_consumed and
first_failed_at out of message headers. Pin both the happy paths and
the defensive defaults so a missing or malformed header never crashes
the consumer mid-loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from kafka_client_py import headers as H
from kafka_client_py.consumer.retry_context import RetryContext
from kafka_client_py.headers import KafkaHeaders


@dataclass
class _Msg:
    topic: str = "events.async"
    partition: int = 0
    offset: int = 0
    key: bytes | None = None
    value: bytes | None = None
    headers: KafkaHeaders | None = field(default_factory=list)


def test_from_message_with_no_headers_defaults_to_zero_attempts_and_no_timestamp():
    ctx = RetryContext.from_message(_Msg(headers=None))

    assert ctx.retry_topic_attempts_consumed == 0
    assert ctx.first_failed_at is None


def test_from_message_empty_headers_behaves_like_none():
    ctx = RetryContext.from_message(_Msg(headers=[]))

    assert ctx.retry_topic_attempts_consumed == 0
    assert ctx.first_failed_at is None


def test_from_message_reads_retry_count_header():
    msg = _Msg(headers=[(H.HEADER_RETRY_COUNT, H.encode(3))])

    ctx = RetryContext.from_message(msg)

    assert ctx.retry_topic_attempts_consumed == 3


def test_from_message_reads_first_failed_at_header():
    failed = datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC)
    msg = _Msg(headers=[(H.HEADER_FIRST_FAILED_AT, H.encode(failed))])

    ctx = RetryContext.from_message(msg)

    assert ctx.first_failed_at == failed


def test_from_message_reads_both_headers_independently():
    failed = datetime(2026, 1, 1, tzinfo=UTC)
    msg = _Msg(
        headers=[
            (H.HEADER_RETRY_COUNT, H.encode(7)),
            (H.HEADER_FIRST_FAILED_AT, H.encode(failed)),
        ]
    )

    ctx = RetryContext.from_message(msg)

    assert ctx.retry_topic_attempts_consumed == 7
    assert ctx.first_failed_at == failed


def test_from_message_malformed_retry_count_defaults_to_zero():
    msg = _Msg(headers=[(H.HEADER_RETRY_COUNT, b"not-a-number")])

    ctx = RetryContext.from_message(msg)

    assert ctx.retry_topic_attempts_consumed == 0


def test_from_message_malformed_first_failed_at_defaults_to_none():
    msg = _Msg(headers=[(H.HEADER_FIRST_FAILED_AT, b"not-a-timestamp")])

    ctx = RetryContext.from_message(msg)

    assert ctx.first_failed_at is None


def test_first_failed_at_or_now_returns_recorded_when_set():
    failed = datetime(2026, 5, 18, tzinfo=UTC)
    ctx = RetryContext(retry_topic_attempts_consumed=1, first_failed_at=failed)

    assert ctx.first_failed_at_or_now() == failed


def test_first_failed_at_or_now_returns_now_in_utc_when_unset():
    ctx = RetryContext(retry_topic_attempts_consumed=0, first_failed_at=None)

    before = datetime.now(UTC)
    result = ctx.first_failed_at_or_now()
    after = datetime.now(UTC)

    assert result.tzinfo == UTC
    assert before <= result <= after


def test_retry_context_is_frozen_dataclass():
    ctx = RetryContext(retry_topic_attempts_consumed=0, first_failed_at=None)

    try:
        ctx.retry_topic_attempts_consumed = 99  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("RetryContext must be frozen — mutation should raise")

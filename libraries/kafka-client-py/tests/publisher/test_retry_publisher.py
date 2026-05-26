"""RetryPublisher: stamps the full retry envelope on the republished message.

The retry topic carries metadata the original consumer must reconstruct
on next attempt:
- x-original-topic / partition / offset (so DLQ can locate the source);
- x-retry-count (the NEXT attempt number, set by the caller);
- x-retry-at (when the scheduler should redeliver);
- x-first-failed-at (when the journey started — preserved across hops);
- x-failed-at (always now);
- x-error-class / message / stack (capped lengths to avoid blowing
  Kafka's per-record header budget);
- x-correlation-id (passthrough or override).

Pin the fallback chains (caller arg → existing header → safe default)
because they're the source of most "missing breadcrumb" bugs.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from kafka_client_py import headers as H
from kafka_client_py.publisher.retry_publisher import RetryPublisher

from tests.fakes import FakeMessage, FakePublisher


def _make_traceback_error(message: str) -> Exception:
    # Raise + catch so the exception has a real __traceback__ attached.
    try:
        raise ValueError(message)
    except ValueError as exc:
        return exc


@pytest.mark.asyncio
async def test_publishes_to_configured_topic_with_message_key_and_value():
    pub = FakePublisher()
    rp = RetryPublisher(pub, topic="events.retry")  # type: ignore[arg-type]

    await rp.publish(
        FakeMessage(key=b"acct-1", value=b"payload"),
        error=ValueError("blip"),
        next_retry_at=datetime(2026, 1, 1, tzinfo=UTC),
        attempt=1,
    )

    out = pub.published[0]
    assert out.topic == "events.retry"
    assert out.key == b"acct-1"
    assert out.value == b"payload"


@pytest.mark.asyncio
async def test_default_topic_is_events_retry():
    pub = FakePublisher()
    rp = RetryPublisher(pub)  # type: ignore[arg-type]

    await rp.publish(
        FakeMessage(),
        error=ValueError(),
        next_retry_at=datetime.now(UTC),
        attempt=1,
    )

    assert pub.published[0].topic == "events.retry"


@pytest.mark.asyncio
async def test_value_defaults_to_empty_bytes_when_message_value_is_none():
    # aiokafka requires bytes, not None — pin defensive coercion.
    pub = FakePublisher()
    rp = RetryPublisher(pub)  # type: ignore[arg-type]

    await rp.publish(
        FakeMessage(value=None),
        error=ValueError(),
        next_retry_at=datetime.now(UTC),
        attempt=1,
    )

    assert pub.published[0].value == b""


# ---------------------------------------------------------------------------
# Original-topic provenance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_original_topic_falls_back_to_message_topic_on_first_retry():
    pub = FakePublisher()
    rp = RetryPublisher(pub)  # type: ignore[arg-type]

    await rp.publish(
        FakeMessage(topic="events.async", headers=[]),
        error=ValueError(),
        next_retry_at=datetime.now(UTC),
        attempt=1,
    )

    assert H.get(pub.published[0].headers, H.HEADER_ORIGINAL_TOPIC) == "events.async"


@pytest.mark.asyncio
async def test_original_topic_preserved_across_hops_via_existing_header():
    # On the 2nd retry, the inbound message arrives FROM events.retry,
    # but x-original-topic is still events.async. Preserve it.
    pub = FakePublisher()
    rp = RetryPublisher(pub)  # type: ignore[arg-type]
    inbound = FakeMessage(
        topic="events.retry",
        headers=[(H.HEADER_ORIGINAL_TOPIC, H.encode("events.async"))],
    )

    await rp.publish(
        inbound,
        error=ValueError(),
        next_retry_at=datetime.now(UTC),
        attempt=2,
    )

    assert H.get(pub.published[0].headers, H.HEADER_ORIGINAL_TOPIC) == "events.async"


@pytest.mark.asyncio
async def test_original_partition_and_offset_stamped_from_inbound_message():
    pub = FakePublisher()
    rp = RetryPublisher(pub)  # type: ignore[arg-type]
    msg = FakeMessage(partition=7, offset=4242)

    await rp.publish(msg, error=ValueError(), next_retry_at=datetime.now(UTC), attempt=1)

    assert H.get_int(pub.published[0].headers, H.HEADER_ORIGINAL_PARTITION) == 7
    assert H.get_int(pub.published[0].headers, H.HEADER_ORIGINAL_OFFSET) == 4242


# ---------------------------------------------------------------------------
# Attempt and retry-at
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attempt_number_is_recorded_verbatim_from_caller():
    pub = FakePublisher()
    rp = RetryPublisher(pub)  # type: ignore[arg-type]

    await rp.publish(FakeMessage(), error=ValueError(), next_retry_at=datetime.now(UTC), attempt=42)

    assert H.get_int(pub.published[0].headers, H.HEADER_RETRY_COUNT) == 42


@pytest.mark.asyncio
async def test_retry_at_is_stamped_with_provided_timestamp():
    pub = FakePublisher()
    rp = RetryPublisher(pub)  # type: ignore[arg-type]
    when = datetime(2026, 6, 1, 10, 30, 0, tzinfo=UTC)

    await rp.publish(FakeMessage(), error=ValueError(), next_retry_at=when, attempt=1)

    assert H.get_datetime(pub.published[0].headers, H.HEADER_RETRY_AT) == when


# ---------------------------------------------------------------------------
# first_failed_at fallback chain
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_first_failed_at_argument_takes_precedence():
    pub = FakePublisher()
    rp = RetryPublisher(pub)  # type: ignore[arg-type]
    explicit = datetime(2026, 3, 1, tzinfo=UTC)
    inbound_recorded = datetime(2026, 2, 1, tzinfo=UTC)

    await rp.publish(
        FakeMessage(headers=[(H.HEADER_FIRST_FAILED_AT, H.encode(inbound_recorded))]),
        error=ValueError(),
        next_retry_at=datetime.now(UTC),
        attempt=1,
        first_failed_at=explicit,
    )

    assert H.get_datetime(pub.published[0].headers, H.HEADER_FIRST_FAILED_AT) == explicit


@pytest.mark.asyncio
async def test_first_failed_at_falls_back_to_inbound_header():
    pub = FakePublisher()
    rp = RetryPublisher(pub)  # type: ignore[arg-type]
    inbound = datetime(2026, 2, 1, tzinfo=UTC)

    await rp.publish(
        FakeMessage(headers=[(H.HEADER_FIRST_FAILED_AT, H.encode(inbound))]),
        error=ValueError(),
        next_retry_at=datetime.now(UTC),
        attempt=1,
    )

    assert H.get_datetime(pub.published[0].headers, H.HEADER_FIRST_FAILED_AT) == inbound


@pytest.mark.asyncio
async def test_first_failed_at_defaults_to_now_when_neither_source_present():
    pub = FakePublisher()
    rp = RetryPublisher(pub)  # type: ignore[arg-type]
    before = datetime.now(UTC)

    await rp.publish(
        FakeMessage(),
        error=ValueError(),
        next_retry_at=datetime.now(UTC),
        attempt=1,
    )

    stamped = H.get_datetime(pub.published[0].headers, H.HEADER_FIRST_FAILED_AT)
    after = datetime.now(UTC)
    assert stamped is not None
    assert before <= stamped <= after


# ---------------------------------------------------------------------------
# Error class / message / stack
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_error_class_is_the_exception_typename():
    pub = FakePublisher()
    rp = RetryPublisher(pub)  # type: ignore[arg-type]

    await rp.publish(
        FakeMessage(),
        error=ConnectionResetError("server hung up"),
        next_retry_at=datetime.now(UTC),
        attempt=1,
    )

    assert H.get(pub.published[0].headers, H.HEADER_ERROR_CLASS) == "ConnectionResetError"


@pytest.mark.asyncio
async def test_error_message_carries_exception_string():
    pub = FakePublisher()
    rp = RetryPublisher(pub)  # type: ignore[arg-type]

    await rp.publish(
        FakeMessage(),
        error=ValueError("bad input"),
        next_retry_at=datetime.now(UTC),
        attempt=1,
    )

    assert H.get(pub.published[0].headers, H.HEADER_ERROR_MESSAGE) == "bad input"


@pytest.mark.asyncio
async def test_error_message_is_truncated_at_1024_chars():
    # Kafka caps per-header bytes; a multi-MB SQL error would blow the budget.
    pub = FakePublisher()
    rp = RetryPublisher(pub)  # type: ignore[arg-type]
    huge_message = "x" * 5000

    await rp.publish(
        FakeMessage(),
        error=ValueError(huge_message),
        next_retry_at=datetime.now(UTC),
        attempt=1,
    )

    decoded = H.get(pub.published[0].headers, H.HEADER_ERROR_MESSAGE)
    assert decoded is not None
    assert len(decoded) == 1024


@pytest.mark.asyncio
async def test_error_stack_is_present_and_capped_at_8192_chars():
    pub = FakePublisher()
    rp = RetryPublisher(pub)  # type: ignore[arg-type]
    exc = _make_traceback_error("blip")

    await rp.publish(FakeMessage(), error=exc, next_retry_at=datetime.now(UTC), attempt=1)

    decoded = H.get(pub.published[0].headers, H.HEADER_ERROR_STACK)
    assert decoded is not None
    assert "ValueError" in decoded
    assert len(decoded) <= 8192


# ---------------------------------------------------------------------------
# correlation_id passthrough
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_correlation_id_from_argument_is_stamped():
    pub = FakePublisher()
    rp = RetryPublisher(pub)  # type: ignore[arg-type]

    await rp.publish(
        FakeMessage(),
        error=ValueError(),
        next_retry_at=datetime.now(UTC),
        attempt=1,
        correlation_id="trace-123",
    )

    assert H.get(pub.published[0].headers, H.HEADER_CORRELATION_ID) == "trace-123"


@pytest.mark.asyncio
async def test_correlation_id_falls_back_to_inbound_header():
    pub = FakePublisher()
    rp = RetryPublisher(pub)  # type: ignore[arg-type]

    await rp.publish(
        FakeMessage(headers=[(H.HEADER_CORRELATION_ID, H.encode("inbound-trace"))]),
        error=ValueError(),
        next_retry_at=datetime.now(UTC),
        attempt=1,
    )

    assert H.get(pub.published[0].headers, H.HEADER_CORRELATION_ID) == "inbound-trace"


@pytest.mark.asyncio
async def test_correlation_id_header_omitted_when_neither_source_present():
    # No correlation id anywhere → don't stamp a placeholder. Downstream
    # consumers treat absence and "-" differently.
    pub = FakePublisher()
    rp = RetryPublisher(pub)  # type: ignore[arg-type]

    await rp.publish(
        FakeMessage(headers=[]),
        error=ValueError(),
        next_retry_at=datetime.now(UTC),
        attempt=1,
    )

    assert H.get(pub.published[0].headers, H.HEADER_CORRELATION_ID) is None


@pytest.mark.asyncio
async def test_argument_correlation_id_overrides_inbound_header():
    pub = FakePublisher()
    rp = RetryPublisher(pub)  # type: ignore[arg-type]

    await rp.publish(
        FakeMessage(headers=[(H.HEADER_CORRELATION_ID, H.encode("stale"))]),
        error=ValueError(),
        next_retry_at=datetime.now(UTC),
        attempt=1,
        correlation_id="fresh",
    )

    # last-wins via H.get on the merged header list
    assert H.get(pub.published[0].headers, H.HEADER_CORRELATION_ID) == "fresh"

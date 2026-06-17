"""DLQPublisher: terminal route. Stamps the full failure envelope.

Mirrors RetryPublisher's behavior minus the retry_at + attempt fields
— the DLQ message is the final hop. Pin the same fallback chains
(original_topic, first_failed_at, correlation_id) and the error-length
caps, since DLQ messages are the ones humans actually read.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fakes import FakeMessage, FakePublisher

from kafka_client_py import headers as H
from kafka_client_py.publisher.dlq_publisher import DLQPublisher


@pytest.mark.asyncio
async def test_publishes_to_configured_topic():
    pub = FakePublisher()
    dlq = DLQPublisher(pub, topic="events.dlq")  # type: ignore[arg-type]

    await dlq.publish(
        FakeMessage(),
        error=ValueError(),
        total_attempts=1,
    )

    assert pub.published[0].topic == "events.dlq"


@pytest.mark.asyncio
async def test_default_topic_is_events_dlq():
    pub = FakePublisher()
    dlq = DLQPublisher(pub)  # type: ignore[arg-type]

    await dlq.publish(FakeMessage(), error=ValueError(), total_attempts=1)

    assert pub.published[0].topic == "events.dlq"


@pytest.mark.asyncio
async def test_preserves_message_key_and_value():
    pub = FakePublisher()
    dlq = DLQPublisher(pub)  # type: ignore[arg-type]

    await dlq.publish(
        FakeMessage(key=b"acct-1", value=b"payload"),
        error=ValueError(),
        total_attempts=1,
    )

    out = pub.published[0]
    assert out.key == b"acct-1"
    assert out.value == b"payload"


@pytest.mark.asyncio
async def test_value_defaults_to_empty_bytes_when_message_value_is_none():
    pub = FakePublisher()
    dlq = DLQPublisher(pub)  # type: ignore[arg-type]

    await dlq.publish(FakeMessage(value=None), error=ValueError(), total_attempts=1)

    assert pub.published[0].value == b""


@pytest.mark.asyncio
async def test_original_topic_taken_from_existing_header_when_present():
    pub = FakePublisher()
    dlq = DLQPublisher(pub)  # type: ignore[arg-type]

    await dlq.publish(
        FakeMessage(
            topic="events.retry",
            headers=[(H.HEADER_ORIGINAL_TOPIC, H.encode("events.async"))],
        ),
        error=ValueError(),
        total_attempts=1,
    )

    assert H.get(pub.published[0].headers, H.HEADER_ORIGINAL_TOPIC) == "events.async"


@pytest.mark.asyncio
async def test_original_topic_falls_back_to_message_topic():
    pub = FakePublisher()
    dlq = DLQPublisher(pub)  # type: ignore[arg-type]

    await dlq.publish(
        FakeMessage(topic="events.async", headers=[]),
        error=ValueError(),
        total_attempts=1,
    )

    assert H.get(pub.published[0].headers, H.HEADER_ORIGINAL_TOPIC) == "events.async"


@pytest.mark.asyncio
async def test_original_partition_and_offset_stamped_from_inbound():
    pub = FakePublisher()
    dlq = DLQPublisher(pub)  # type: ignore[arg-type]

    await dlq.publish(
        FakeMessage(partition=3, offset=999),
        error=ValueError(),
        total_attempts=1,
    )

    assert H.get_int(pub.published[0].headers, H.HEADER_ORIGINAL_PARTITION) == 3
    assert H.get_int(pub.published[0].headers, H.HEADER_ORIGINAL_OFFSET) == 999


@pytest.mark.asyncio
async def test_retry_count_records_total_attempts_argument():
    pub = FakePublisher()
    dlq = DLQPublisher(pub)  # type: ignore[arg-type]

    await dlq.publish(FakeMessage(), error=ValueError(), total_attempts=17)

    assert H.get_int(pub.published[0].headers, H.HEADER_RETRY_COUNT) == 17


@pytest.mark.asyncio
async def test_first_failed_at_argument_takes_precedence():
    pub = FakePublisher()
    dlq = DLQPublisher(pub)  # type: ignore[arg-type]
    explicit = datetime(2026, 3, 1, tzinfo=UTC)

    await dlq.publish(
        FakeMessage(
            headers=[(H.HEADER_FIRST_FAILED_AT, H.encode(datetime(2026, 1, 1, tzinfo=UTC)))]
        ),
        error=ValueError(),
        total_attempts=1,
        first_failed_at=explicit,
    )

    assert H.get_datetime(pub.published[0].headers, H.HEADER_FIRST_FAILED_AT) == explicit


@pytest.mark.asyncio
async def test_first_failed_at_falls_back_to_inbound_header():
    pub = FakePublisher()
    dlq = DLQPublisher(pub)  # type: ignore[arg-type]
    inbound = datetime(2026, 1, 1, tzinfo=UTC)

    await dlq.publish(
        FakeMessage(headers=[(H.HEADER_FIRST_FAILED_AT, H.encode(inbound))]),
        error=ValueError(),
        total_attempts=1,
    )

    assert H.get_datetime(pub.published[0].headers, H.HEADER_FIRST_FAILED_AT) == inbound


@pytest.mark.asyncio
async def test_first_failed_at_defaults_to_now_when_neither_source_present():
    pub = FakePublisher()
    dlq = DLQPublisher(pub)  # type: ignore[arg-type]
    before = datetime.now(UTC)

    await dlq.publish(FakeMessage(), error=ValueError(), total_attempts=1)

    stamped = H.get_datetime(pub.published[0].headers, H.HEADER_FIRST_FAILED_AT)
    after = datetime.now(UTC)
    assert stamped is not None
    assert before <= stamped <= after


@pytest.mark.asyncio
async def test_error_class_message_and_stack_are_stamped():
    pub = FakePublisher()
    dlq = DLQPublisher(pub)  # type: ignore[arg-type]
    try:
        raise ConnectionResetError("hung up")
    except ConnectionResetError as exc:
        await dlq.publish(FakeMessage(), error=exc, total_attempts=1)

    out = pub.published[0]
    assert H.get(out.headers, H.HEADER_ERROR_CLASS) == "ConnectionResetError"
    assert H.get(out.headers, H.HEADER_ERROR_MESSAGE) == "hung up"
    stack = H.get(out.headers, H.HEADER_ERROR_STACK)
    assert stack is not None and "ConnectionResetError" in stack


@pytest.mark.asyncio
async def test_error_message_capped_at_1024_chars():
    pub = FakePublisher()
    dlq = DLQPublisher(pub)  # type: ignore[arg-type]

    await dlq.publish(
        FakeMessage(),
        error=ValueError("x" * 5000),
        total_attempts=1,
    )

    decoded = H.get(pub.published[0].headers, H.HEADER_ERROR_MESSAGE)
    assert decoded is not None and len(decoded) == 1024


@pytest.mark.asyncio
async def test_failed_at_header_is_set_to_now():
    pub = FakePublisher()
    dlq = DLQPublisher(pub)  # type: ignore[arg-type]
    before = datetime.now(UTC)

    await dlq.publish(FakeMessage(), error=ValueError(), total_attempts=1)

    failed_at = H.get_datetime(pub.published[0].headers, H.HEADER_FAILED_AT)
    after = datetime.now(UTC)
    assert failed_at is not None
    assert before <= failed_at <= after


@pytest.mark.asyncio
async def test_correlation_id_argument_is_stamped():
    pub = FakePublisher()
    dlq = DLQPublisher(pub)  # type: ignore[arg-type]

    await dlq.publish(
        FakeMessage(),
        error=ValueError(),
        total_attempts=1,
        correlation_id="trace-9",
    )

    assert H.get(pub.published[0].headers, H.HEADER_CORRELATION_ID) == "trace-9"


@pytest.mark.asyncio
async def test_correlation_id_falls_back_to_inbound_header():
    pub = FakePublisher()
    dlq = DLQPublisher(pub)  # type: ignore[arg-type]

    await dlq.publish(
        FakeMessage(headers=[(H.HEADER_CORRELATION_ID, H.encode("inbound-trace"))]),
        error=ValueError(),
        total_attempts=1,
    )

    assert H.get(pub.published[0].headers, H.HEADER_CORRELATION_ID) == "inbound-trace"


@pytest.mark.asyncio
async def test_correlation_id_header_omitted_when_neither_source_present():
    pub = FakePublisher()
    dlq = DLQPublisher(pub)  # type: ignore[arg-type]

    await dlq.publish(
        FakeMessage(headers=[]),
        error=ValueError(),
        total_attempts=1,
    )

    assert H.get(pub.published[0].headers, H.HEADER_CORRELATION_ID) is None

from __future__ import annotations

from datetime import timedelta

import pytest
from fakes import FakeMessage, FakePublisher

from kafka_client_py import (
    DLQPublisher,
    InMemoryDedupeStore,
    MessageHandler,
    PoisonError,
    RetryPolicy,
    RetryPublisher,
    TransientError,
)
from kafka_client_py import headers as H


def _wire(policy: RetryPolicy, user_handler):
    pub = FakePublisher()
    retry = RetryPublisher(pub, topic="events.retry")  # type: ignore[arg-type]
    dlq = DLQPublisher(pub, topic="events.dlq")  # type: ignore[arg-type]
    handler = MessageHandler(
        user_handler,
        policy=policy,
        retry_publisher=retry,
        dlq_publisher=dlq,
    )
    return handler, pub


@pytest.mark.asyncio
async def test_success_no_publish():
    calls = 0

    async def ok(_msg):
        nonlocal calls
        calls += 1

    handler, pub = _wire(RetryPolicy(), ok)
    await handler.handle(FakeMessage())

    assert calls == 1
    assert pub.published == []


@pytest.mark.asyncio
async def test_poison_routes_to_dlq_immediately():
    calls = 0

    async def boom(_msg):
        nonlocal calls
        calls += 1
        raise PoisonError("bad payload")

    handler, pub = _wire(RetryPolicy(max_in_process_attempts=3), boom)
    await handler.handle(FakeMessage())

    assert calls == 1
    assert len(pub.published) == 1
    assert pub.published[0].topic == "events.dlq"


@pytest.mark.asyncio
async def test_transient_then_success_in_process():
    calls = 0

    async def flaky(_msg):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise TransientError("blip")

    policy = RetryPolicy(
        max_in_process_attempts=3,
        initial_backoff=timedelta(seconds=0),
        jitter_ratio=0.0,
    )
    handler, pub = _wire(policy, flaky)
    await handler.handle(FakeMessage())

    assert calls == 3
    assert pub.published == []


@pytest.mark.asyncio
async def test_transient_exhausts_in_process_then_publishes_retry():
    async def always_fail(_msg):
        raise TransientError("still blipping")

    policy = RetryPolicy(
        max_in_process_attempts=2,
        max_retry_topic_attempts=5,
        initial_backoff=timedelta(seconds=1),
        jitter_ratio=0.0,
    )
    handler, pub = _wire(policy, always_fail)
    await handler.handle(FakeMessage())

    assert len(pub.published) == 1
    pub_out = pub.published[0]
    assert pub_out.topic == "events.retry"
    assert H.get(pub_out.headers, H.HEADER_RETRY_COUNT) == "1"
    assert H.get(pub_out.headers, H.HEADER_ORIGINAL_TOPIC) == "events.async"
    assert H.get(pub_out.headers, H.HEADER_ERROR_CLASS) == "TransientError"


@pytest.mark.asyncio
async def test_retry_budget_exhausted_routes_to_dlq():
    async def always_fail(_msg):
        raise TransientError("dead")

    policy = RetryPolicy(
        max_in_process_attempts=1,
        max_retry_topic_attempts=3,
        initial_backoff=timedelta(seconds=0),
        jitter_ratio=0.0,
    )
    handler, pub = _wire(policy, always_fail)

    msg = FakeMessage(headers=[(H.HEADER_RETRY_COUNT, H.encode(3))])
    await handler.handle(msg)

    assert len(pub.published) == 1
    assert pub.published[0].topic == "events.dlq"


@pytest.mark.asyncio
async def test_non_retryable_unknown_error_goes_to_dlq():
    async def boom(_msg):
        raise ValueError("not in retryable tuple")

    policy = RetryPolicy(retryable=(ConnectionError,))
    handler, pub = _wire(policy, boom)
    await handler.handle(FakeMessage())

    assert len(pub.published) == 1
    assert pub.published[0].topic == "events.dlq"


@pytest.mark.asyncio
async def test_dedupe_skips_seen_event():
    calls = 0

    async def user_handler(_msg):
        nonlocal calls
        calls += 1

    dedupe = InMemoryDedupeStore()
    await dedupe.mark("evt-1")

    pub = FakePublisher()
    handler = MessageHandler(
        user_handler,
        policy=RetryPolicy(),
        retry_publisher=RetryPublisher(pub, topic="events.retry"),  # type: ignore[arg-type]
        dlq_publisher=DLQPublisher(pub, topic="events.dlq"),  # type: ignore[arg-type]
        dedupe=dedupe,
        event_id=lambda _m: "evt-1",
    )

    await handler.handle(FakeMessage())

    assert calls == 0
    assert pub.published == []

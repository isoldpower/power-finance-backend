"""AsyncPublisher: lifecycle (start/stop/idempotent), guard before start,
and the context-manager helper.

The real producer is aiokafka.AIOKafkaProducer — we patch it so tests
don't require a running broker. The class is instantiated and started
exactly the way the real one would be; we just observe the calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kafka_client_py.publisher.publisher import AsyncPublisher, ProducerConfig


def _producer_mock() -> MagicMock:
    """Stand-in for AIOKafkaProducer with async start/stop/send_and_wait."""
    producer = MagicMock()
    producer.start = AsyncMock()
    producer.stop = AsyncMock()
    producer.send_and_wait = AsyncMock()
    return producer


def _config(**overrides) -> ProducerConfig:
    defaults = {"bootstrap_servers": "localhost:9092"}
    defaults.update(overrides)
    return ProducerConfig(**defaults)


# ---------------------------------------------------------------------------
# ProducerConfig
# ---------------------------------------------------------------------------


def test_producer_config_defaults_match_documented_safety_settings():
    # acks=all + idempotence=True is the durability story; if either
    # default flips, services lose at-least-once guarantees silently.
    cfg = ProducerConfig(bootstrap_servers="localhost:9092")

    assert cfg.acknowledgement_mode == "all"
    assert cfg.enable_idempotence is True
    assert cfg.linger_milliseconds == 5
    assert cfg.compression_type == "gzip"
    assert cfg.client_id is None


# ---------------------------------------------------------------------------
# start / stop lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_constructs_and_starts_inner_producer():
    producer = _producer_mock()
    with patch(
        "kafka_client_py.publisher.publisher.AIOKafkaProducer",
        return_value=producer,
    ) as ProducerCls:
        publisher = AsyncPublisher(_config(client_id="cid", linger_milliseconds=10))

        await publisher.start()

    ProducerCls.assert_called_once_with(
        bootstrap_servers="localhost:9092",
        client_id="cid",
        acks="all",
        enable_idempotence=True,
        linger_ms=10,
        compression_type="gzip",
    )
    producer.start.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_is_idempotent():
    # Already-started → second call is a no-op (no second producer, no
    # second start). Important for service bootstrap that may race.
    producer = _producer_mock()
    with patch(
        "kafka_client_py.publisher.publisher.AIOKafkaProducer",
        return_value=producer,
    ) as ProducerCls:
        publisher = AsyncPublisher(_config())

        await publisher.start()
        await publisher.start()

    assert ProducerCls.call_count == 1
    producer.start.assert_awaited_once()


@pytest.mark.asyncio
async def test_stop_without_start_is_a_silent_noop():
    # Service shutdown might call stop() before start() in error paths;
    # this must not crash.
    publisher = AsyncPublisher(_config())

    await publisher.stop()  # must not raise


@pytest.mark.asyncio
async def test_stop_stops_the_inner_producer_and_clears_handle():
    producer = _producer_mock()
    with patch(
        "kafka_client_py.publisher.publisher.AIOKafkaProducer",
        return_value=producer,
    ):
        publisher = AsyncPublisher(_config())
        await publisher.start()

        await publisher.stop()

    producer.stop.assert_awaited_once()
    # Subsequent stop must still no-op (handle was cleared).
    await publisher.stop()
    producer.stop.assert_awaited_once()  # not awaited a second time


# ---------------------------------------------------------------------------
# publish
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_before_start_raises_runtime_error():
    # Defensive: tells the caller they forgot the lifecycle hook.
    publisher = AsyncPublisher(_config())

    with pytest.raises(RuntimeError, match="before start"):
        await publisher.publish("t", value=b"x")


@pytest.mark.asyncio
async def test_publish_forwards_args_to_inner_producer():
    producer = _producer_mock()
    with patch(
        "kafka_client_py.publisher.publisher.AIOKafkaProducer",
        return_value=producer,
    ):
        publisher = AsyncPublisher(_config())
        await publisher.start()

        await publisher.publish(
            "events.async",
            value=b"payload",
            key=b"acct-1",
            headers=[("x", b"1")],
        )

    producer.send_and_wait.assert_awaited_once_with(
        topic="events.async",
        value=b"payload",
        key=b"acct-1",
        headers=[("x", b"1")],
    )


@pytest.mark.asyncio
async def test_publish_with_no_headers_passes_empty_list_not_none():
    # aiokafka rejects None headers — pin the empty-list defaulting.
    producer = _producer_mock()
    with patch(
        "kafka_client_py.publisher.publisher.AIOKafkaProducer",
        return_value=producer,
    ):
        publisher = AsyncPublisher(_config())
        await publisher.start()

        await publisher.publish("t", value=b"x")

    kwargs = producer.send_and_wait.await_args.kwargs
    assert kwargs["headers"] == []
    assert kwargs["key"] is None


# ---------------------------------------------------------------------------
# async context manager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_context_manager_starts_on_enter_and_stops_on_exit():
    producer = _producer_mock()
    with patch(
        "kafka_client_py.publisher.publisher.AIOKafkaProducer",
        return_value=producer,
    ):
        async with AsyncPublisher(_config()) as publisher:
            assert publisher is not None
            await publisher.publish("t", value=b"x")
            producer.start.assert_awaited_once()
            producer.stop.assert_not_awaited()

    producer.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_context_manager_stops_even_when_body_raises():
    producer = _producer_mock()
    with (
        patch("kafka_client_py.publisher.publisher.AIOKafkaProducer", return_value=producer),
        pytest.raises(RuntimeError),
    ):
        async with AsyncPublisher(_config()):
            raise RuntimeError("boom")

    producer.stop.assert_awaited_once()

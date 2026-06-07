"""Health probes, backoff polling, and the consumption-blocking guard."""

import asyncio

import pytest

from data_read_core.shared.health_guard import (
    ElasticsearchHealthProbe,
    HealthGuardedHandler,
    HealthProbe,
    RedisHealthProbe,
)
from data_read_core.shared.health_guard import (
    elasticsearch_health_probe as es_probe_module,
)
from data_read_core.shared.health_guard import (
    redis_health_probe as redis_probe_module,
)
from data_read_core.shared.kafka_updates import EventMessage


def _event() -> EventMessage:
    return EventMessage(
        event_id="evt-1",
        event_type="WalletCreated",
        aggregate_type="wallet",
        aggregate_id="w1",
        outbox_seq=1,
        payload=b"{}",
        headers={},
        topic="events.async",
        partition=0,
        offset=0,
    )


class _ScriptedProbe(HealthProbe):
    """Health flips according to a scripted sequence of booleans."""

    def __init__(self, results: list[bool]) -> None:
        super().__init__(initial_poll_seconds=0.0, max_poll_seconds=0.0)
        self._results = list(results)
        self.checks = 0

    @property
    def name(self) -> str:
        return "scripted"

    async def is_healthy(self) -> bool:
        self.checks += 1
        return self._results.pop(0)


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    async def _instant(_seconds):
        return None

    monkeypatch.setattr(asyncio, "sleep", _instant)


async def test_wait_until_healthy_returns_once_healthy():
    probe = _ScriptedProbe([False, False, True])

    await probe.wait_until_healthy()

    assert probe.checks == 3


async def test_wait_until_healthy_returns_immediately_when_already_healthy():
    probe = _ScriptedProbe([True])

    await probe.wait_until_healthy()

    assert probe.checks == 1


async def test_guarded_handler_retries_until_dependency_recovers():
    attempts = {"n": 0}

    seen: list[EventMessage] = []

    async def flaky_handler(event):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise ConnectionError("redis down")
        seen.append(event)

    class _RecoverProbe(HealthProbe):
        def __init__(self):
            super().__init__()
            self.waited = 0

        @property
        def name(self):
            return "redis"

        async def is_healthy(self):
            return True

        async def wait_until_healthy(self):
            self.waited += 1

    probe = _RecoverProbe()
    handler = HealthGuardedHandler(flaky_handler, probe, guarded_errors=(ConnectionError,))

    await handler(_event())  # must not raise; retries after the outage

    assert attempts["n"] == 2
    assert probe.waited == 1
    assert len(seen) == 1  # second attempt succeeded


async def test_guarded_handler_passes_through_on_success():
    calls: list[str] = []

    async def handler(event):
        calls.append(event)

    class _Probe(HealthProbe):
        @property
        def name(self):
            return "x"

        async def is_healthy(self):
            return True

    await HealthGuardedHandler(handler, _Probe(), guarded_errors=(ConnectionError,))(event="e")

    assert calls == ["e"]


# --------------------------------------------------------------------------- #
# Concrete probe ping behaviour
# --------------------------------------------------------------------------- #
class _FakePingClient:
    def __init__(self, *, result=True, raises=None):
        self._result = result
        self._raises = raises

    async def ping(self):
        if self._raises is not None:
            raise self._raises
        return self._result


async def test_elasticsearch_probe_healthy_when_ping_ok(monkeypatch):
    monkeypatch.setattr(es_probe_module, "get_elasticsearch", lambda: _FakePingClient(result=True))
    assert await ElasticsearchHealthProbe().is_healthy() is True


async def test_elasticsearch_probe_unhealthy_on_connectivity_error(monkeypatch):
    monkeypatch.setattr(
        es_probe_module, "get_elasticsearch", lambda: _FakePingClient(raises=OSError("no route"))
    )
    assert await ElasticsearchHealthProbe().is_healthy() is False


async def test_redis_probe_healthy_when_ping_ok(monkeypatch):
    monkeypatch.setattr(redis_probe_module, "get_redis", lambda: _FakePingClient(result=True))
    assert await RedisHealthProbe().is_healthy() is True


async def test_redis_probe_unhealthy_on_connectivity_error(monkeypatch):
    monkeypatch.setattr(
        redis_probe_module, "get_redis", lambda: _FakePingClient(raises=OSError("down"))
    )
    assert await RedisHealthProbe().is_healthy() is False

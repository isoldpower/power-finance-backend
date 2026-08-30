"""Probe backoff polling and the consumption-blocking guard.

The concrete probes each service wires in are tested where they live; what
is here is the contract they are written against."""

import asyncio

import pytest

from kafka_consumer_py import EventMessage
from kafka_consumer_py.health import HealthGuardedHandler, HealthProbe


def _event() -> EventMessage:
    return EventMessage(
        event_id="evt-1",
        event_type="WalletCreated",
        aggregate_type="wallet",
        partition_key="w1",
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

    await handler(_event())

    assert attempts["n"] == 2
    assert probe.waited == 1
    assert len(seen) == 1


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

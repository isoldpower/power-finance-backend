"""Effect coercion, the sequential/atomic process group, and execution plan."""

import pytest

from kafka_consumer_py import EventMessage, ExecutionPlan, SyncProcessGroup
from kafka_consumer_py.processing.effect import Effect, as_effect


def _event() -> EventMessage:
    return EventMessage(
        event_id="e1",
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


class RecordingEffect(Effect):
    def __init__(self, name: str, log: list[str], *, fail: bool = False) -> None:
        self._name = name
        self._log = log
        self._fail = fail

    @property
    def name(self) -> str:
        return self._name

    async def apply(self, event: EventMessage) -> None:
        self._log.append(f"apply:{self._name}")
        if self._fail:
            raise RuntimeError(f"apply failed: {self._name}")

    async def compensate(self, event: EventMessage) -> None:
        self._log.append(f"compensate:{self._name}")


def test_as_effect_passes_through_effect_instances():
    effect = RecordingEffect("a", [])
    assert as_effect(effect) is effect


async def test_as_effect_wraps_async_function_and_keeps_its_name():
    seen: list[EventMessage] = []

    async def index_document(event):
        seen.append(event)

    wrapped = as_effect(index_document)

    assert wrapped.name == "index_document"
    await wrapped.apply(_event())
    assert len(seen) == 1


def test_effect_default_name_is_class_name():
    assert RecordingEffect.__name__ == "RecordingEffect"


def test_group_requires_at_least_one_effect():
    with pytest.raises(ValueError):
        SyncProcessGroup([])


async def test_non_atomic_group_runs_effects_sequentially():
    log: list[str] = []
    group = SyncProcessGroup([RecordingEffect("a", log), RecordingEffect("b", log)])

    await group.run(_event())

    assert log == ["apply:a", "apply:b"]


async def test_atomic_group_compensates_applied_effects_on_failure():
    log: list[str] = []
    group = SyncProcessGroup(
        [RecordingEffect("a", log), RecordingEffect("b", log, fail=True)],
        atomic=True,
    )

    with pytest.raises(RuntimeError, match="apply failed: b"):
        await group.run(_event())

    assert log == ["apply:a", "apply:b", "compensate:a"]


def test_plan_requires_at_least_one_group():
    with pytest.raises(ValueError):
        ExecutionPlan([])


async def test_plan_runs_every_group():
    log: list[str] = []
    plan = ExecutionPlan(
        [
            SyncProcessGroup([RecordingEffect("a", log)]),
            SyncProcessGroup([RecordingEffect("b", log)]),
        ]
    )

    await plan(_event())

    assert sorted(log) == ["apply:a", "apply:b"]


async def test_plan_propagates_a_single_group_failure():
    log: list[str] = []
    plan = ExecutionPlan([SyncProcessGroup([RecordingEffect("a", log, fail=True)])])

    with pytest.raises(RuntimeError, match="apply failed: a"):
        await plan(_event())


async def test_plan_aggregates_multiple_group_failures():
    log: list[str] = []
    plan = ExecutionPlan(
        [
            SyncProcessGroup([RecordingEffect("a", log, fail=True)]),
            SyncProcessGroup([RecordingEffect("b", log, fail=True)]),
        ]
    )

    with pytest.raises(BaseExceptionGroup) as excinfo:
        await plan(_event())

    assert len(excinfo.value.exceptions) == 2


class UncompensatedEffect(Effect):
    async def apply(self, event: EventMessage) -> None:
        return None


async def test_an_effect_without_compensation_warns_when_it_is_asked_to_compensate(caplog):
    with caplog.at_level("WARNING", logger="kafka_consumer_py.processing"):
        await UncompensatedEffect().compensate(_event())

    assert "UncompensatedEffect" in caplog.text
    assert "WalletCreated" in caplog.text
    assert "e1" in caplog.text


async def test_an_atomic_group_warns_for_each_uncompensated_effect_it_unwinds(caplog):
    log: list[str] = []
    group = SyncProcessGroup(
        [
            UncompensatedEffect(),
            RecordingEffect("b", log, fail=True),
        ],
        atomic=True,
    )

    with (
        caplog.at_level("WARNING", logger="kafka_consumer_py.processing"),
        pytest.raises(RuntimeError),
    ):
        await group.run(_event())

    assert "UncompensatedEffect" in caplog.text


async def test_a_bare_function_effect_warns_because_it_cannot_compensate(caplog):
    async def evict_cache(event: EventMessage) -> None:
        return None

    with caplog.at_level("WARNING", logger="kafka_consumer_py.processing"):
        await as_effect(evict_cache).compensate(_event())

    assert "evict_cache" in caplog.text

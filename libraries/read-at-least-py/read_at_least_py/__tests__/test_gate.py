import pytest

from read_at_least_py import NotCaughtUp, ReadAtLeastGate


class StubReader:
    def __init__(self, applied: dict[str, int | None]) -> None:
        self._applied = applied
        self.calls: list[str] = []

    async def applied_seq(self, scope: str) -> int | None:
        self.calls.append(scope)
        return self._applied.get(scope)


async def test_none_requirement_short_circuits_without_reading():
    reader = StubReader({})
    gate = ReadAtLeastGate(reader)

    await gate.ensure_caught_up("42", None)

    assert reader.calls == []


async def test_applied_equal_to_required_is_caught_up():
    gate = ReadAtLeastGate(StubReader({"42": 100}))

    await gate.ensure_caught_up("42", 100)


async def test_applied_ahead_of_required_is_caught_up():
    gate = ReadAtLeastGate(StubReader({"42": 150}))

    await gate.ensure_caught_up("42", 100)


async def test_applied_behind_required_raises():
    gate = ReadAtLeastGate(StubReader({"42": 99}))

    with pytest.raises(NotCaughtUp) as exc_info:
        await gate.ensure_caught_up("42", 100)

    assert exc_info.value.required == 100
    assert exc_info.value.applied == 99
    assert exc_info.value.scope == "42"


async def test_nothing_applied_yet_raises():
    gate = ReadAtLeastGate(StubReader({}))

    with pytest.raises(NotCaughtUp) as exc_info:
        await gate.ensure_caught_up("42", 1)

    assert exc_info.value.applied is None


async def test_scope_isolation():
    gate = ReadAtLeastGate(StubReader({"1": 100, "2": 5}))

    await gate.ensure_caught_up("1", 100)
    with pytest.raises(NotCaughtUp):
        await gate.ensure_caught_up("2", 100)

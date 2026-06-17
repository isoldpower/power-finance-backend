import pytest
from fakes import RecordingStep

from saga_pattern_py import SagaCoordinator


def test_requires_at_least_one_step():
    with pytest.raises(ValueError):
        SagaCoordinator([])


async def test_runs_forward_in_order_and_returns_results():
    log: list[tuple[str, str]] = []
    steps = [
        RecordingStep("a", log, result=1),
        RecordingStep("b", log, result=2),
        RecordingStep("c", log, result=3),
    ]

    results = await SagaCoordinator(steps).run()

    assert results == [1, 2, 3]
    assert log == [("forward", "a"), ("forward", "b"), ("forward", "c")]


async def test_compensates_completed_steps_in_reverse_on_forward_failure():
    log: list[tuple[str, str]] = []
    steps = [
        RecordingStep("a", log),
        RecordingStep("b", log),
        RecordingStep("c", log, fail_forward=True),
    ]

    with pytest.raises(RuntimeError, match="forward failed: c"):
        await SagaCoordinator(steps).run()

    assert log == [
        ("forward", "a"),
        ("forward", "b"),
        ("forward", "c"),
        ("compensate", "b"),
        ("compensate", "a"),
    ]


async def test_failure_on_first_step_compensates_nothing():
    log: list[tuple[str, str]] = []
    steps = [RecordingStep("a", log, fail_forward=True)]

    with pytest.raises(RuntimeError, match="forward failed: a"):
        await SagaCoordinator(steps).run()

    assert log == [("forward", "a")]


async def test_compensation_failure_is_swallowed_and_original_error_raised():
    log: list[tuple[str, str]] = []
    steps = [
        RecordingStep("a", log, fail_compensate=True),
        RecordingStep("b", log, fail_forward=True),
    ]

    with pytest.raises(RuntimeError, match="forward failed: b"):
        await SagaCoordinator(steps).run()

    assert ("compensate", "a") in log

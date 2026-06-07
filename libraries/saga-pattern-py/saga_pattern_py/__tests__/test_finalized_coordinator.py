import pytest
from fakes import RecordingStep

from saga_pattern_py import FinalizedSagaCoordinator


def test_requires_at_least_one_transaction_step():
    with pytest.raises(ValueError):
        FinalizedSagaCoordinator(
            transaction_steps=[],
            final_step=RecordingStep("final", []),
        )


async def test_runs_transactions_then_final_and_returns_final_result():
    log: list[tuple[str, str]] = []
    coordinator = FinalizedSagaCoordinator(
        transaction_steps=[RecordingStep("t1", log), RecordingStep("t2", log)],
        final_step=RecordingStep("final", log, result="FINAL"),
    )

    result = await coordinator.run_transaction()

    assert result == "FINAL"
    assert log == [("forward", "t1"), ("forward", "t2"), ("forward", "final")]


async def test_transaction_failure_rolls_back_completed_and_skips_final():
    log: list[tuple[str, str]] = []
    coordinator = FinalizedSagaCoordinator(
        transaction_steps=[RecordingStep("t1", log), RecordingStep("t2", log, fail_forward=True)],
        final_step=RecordingStep("final", log),
    )

    with pytest.raises(RuntimeError, match="forward failed: t2"):
        await coordinator.run_transaction()

    # final never runs; only the completed t1 is compensated.
    assert log == [
        ("forward", "t1"),
        ("forward", "t2"),
        ("compensate", "t1"),
    ]


async def test_final_failure_rolls_back_all_transaction_steps():
    log: list[tuple[str, str]] = []
    coordinator = FinalizedSagaCoordinator(
        transaction_steps=[RecordingStep("t1", log), RecordingStep("t2", log)],
        final_step=RecordingStep("final", log, fail_forward=True),
    )

    with pytest.raises(RuntimeError, match="forward failed: final"):
        await coordinator.run_transaction()

    # final failed forward so it is not compensated; t2 then t1 roll back.
    assert log == [
        ("forward", "t1"),
        ("forward", "t2"),
        ("forward", "final"),
        ("compensate", "t2"),
        ("compensate", "t1"),
    ]

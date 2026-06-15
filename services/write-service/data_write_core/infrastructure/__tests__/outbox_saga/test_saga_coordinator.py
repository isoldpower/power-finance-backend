"""FinalizedSagaCoordinator forward execution + rollback contract: ordered
steps, reverse compensation on failure, swallowed compensation errors."""

from __future__ import annotations

from unittest import IsolatedAsyncioTestCase

from django.test import SimpleTestCase
from saga_pattern_py import FinalizedSagaCoordinator, SagaStep

from data_write_core.infrastructure.outbox_saga.postgres_outbox_step import OutboxSagaStep


class _RecordingStep(SagaStep[None]):
    def __init__(
        self,
        log: list[str],
        label: str,
        *,
        forward_raises: Exception | None = None,
        compensate_raises: Exception | None = None,
    ) -> None:
        self._log = log
        self._label = label
        self._forward_raises = forward_raises
        self._compensate_raises = compensate_raises

    @property
    def name(self) -> str:
        return self._label

    async def forward(self) -> None:
        self._log.append(f"forward:{self._label}")
        if self._forward_raises is not None:
            raise self._forward_raises

    async def compensate(self) -> None:
        self._log.append(f"compensate:{self._label}")
        if self._compensate_raises is not None:
            raise self._compensate_raises


class _RecordingFinalStep(OutboxSagaStep):
    def __init__(
        self,
        log: list[str],
        label: str = "final",
        *,
        forward_raises: Exception | None = None,
        return_sequence: int = 100,
    ) -> None:
        super().__init__()
        self._log = log
        self._label = label
        self._forward_raises = forward_raises
        self._return_sequence = return_sequence

    @property
    def name(self) -> str:
        return self._label

    async def forward(self) -> int:
        self._log.append(f"forward:{self._label}")
        if self._forward_raises is not None:
            raise self._forward_raises
        self._appended_sequences.append(self._return_sequence)
        return self._return_sequence

    async def compensate(self) -> None:
        self._log.append(f"compensate:{self._label}")


class FinalizedSagaCoordinatorConstructionTests(SimpleTestCase):
    def test_rejects_empty_transaction_steps(self) -> None:
        with self.assertRaises(ValueError):
            FinalizedSagaCoordinator(
                transaction_steps=[],
                final_step=_RecordingFinalStep(log=[]),
            )


class FinalizedSagaCoordinatorHappyPathTests(IsolatedAsyncioTestCase):
    async def test_runs_steps_in_order_then_final_and_returns_sequence(self) -> None:
        log: list[str] = []
        coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                _RecordingStep(log, "a"),
                _RecordingStep(log, "b"),
            ],
            final_step=_RecordingFinalStep(log, return_sequence=77),
        )

        result = await coordinator.run_transaction()

        self.assertEqual(result, 77)
        self.assertEqual(log, ["forward:a", "forward:b", "forward:final"])

    async def test_does_not_invoke_compensations_on_success(self) -> None:
        log: list[str] = []
        coordinator = FinalizedSagaCoordinator(
            transaction_steps=[_RecordingStep(log, "a")],
            final_step=_RecordingFinalStep(log),
        )

        await coordinator.run_transaction()

        self.assertNotIn("compensate:a", log)
        self.assertNotIn("compensate:final", log)


class FinalizedSagaCoordinatorRollbackTests(IsolatedAsyncioTestCase):
    async def test_rolls_back_completed_steps_in_reverse_when_middle_step_fails(self) -> None:
        log: list[str] = []
        boom = RuntimeError("step c broke")
        coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                _RecordingStep(log, "a"),
                _RecordingStep(log, "b"),
                _RecordingStep(log, "c", forward_raises=boom),
            ],
            final_step=_RecordingFinalStep(log),
        )

        with self.assertRaises(RuntimeError):
            await coordinator.run_transaction()

        self.assertEqual(
            log,
            [
                "forward:a",
                "forward:b",
                "forward:c",
                "compensate:b",
                "compensate:a",
            ],
        )

    async def test_first_step_failure_compensates_nothing(self) -> None:
        log: list[str] = []
        boom = RuntimeError("first step")
        coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                _RecordingStep(log, "a", forward_raises=boom),
                _RecordingStep(log, "b"),
            ],
            final_step=_RecordingFinalStep(log),
        )

        with self.assertRaises(RuntimeError):
            await coordinator.run_transaction()

        self.assertEqual(log, ["forward:a"])

    async def test_final_step_failure_compensates_all_transaction_steps(self) -> None:
        log: list[str] = []
        boom = RuntimeError("outbox down")
        coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                _RecordingStep(log, "a"),
                _RecordingStep(log, "b"),
            ],
            final_step=_RecordingFinalStep(log, forward_raises=boom),
        )

        with self.assertRaises(RuntimeError):
            await coordinator.run_transaction()

        self.assertEqual(
            log,
            [
                "forward:a",
                "forward:b",
                "forward:final",
                "compensate:b",
                "compensate:a",
            ],
        )

    async def test_compensation_exception_is_swallowed_and_others_run(self) -> None:
        log: list[str] = []
        forward_boom = RuntimeError("c forward")
        coordinator = FinalizedSagaCoordinator(
            transaction_steps=[
                _RecordingStep(log, "a"),
                _RecordingStep(log, "b", compensate_raises=RuntimeError("b comp")),
                _RecordingStep(log, "c", forward_raises=forward_boom),
            ],
            final_step=_RecordingFinalStep(log),
        )

        with self.assertRaises(RuntimeError) as ctx:
            await coordinator.run_transaction()

        self.assertIs(ctx.exception, forward_boom)
        self.assertIn("compensate:b", log)
        self.assertIn("compensate:a", log)


class OutboxStepLastAppendedTests(IsolatedAsyncioTestCase):
    async def test_last_appended_sequence_raises_before_forward(self) -> None:
        step = _RecordingFinalStep(log=[])

        with self.assertRaises(RuntimeError):
            _ = step.last_appended_sequence

    async def test_last_appended_sequence_returns_after_forward(self) -> None:
        step = _RecordingFinalStep(log=[], return_sequence=42)

        await step.forward()

        self.assertEqual(step.last_appended_sequence, 42)

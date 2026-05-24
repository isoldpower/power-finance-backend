import logging
from typing import Any

from .saga_step import OutboxSagaStep, SagaStep

logger = logging.getLogger(__name__)


class SagaCoordinator:
    """Linear SAGA orchestrator with a distinguished final step.

    Two-phase run:
    1. `transaction_steps` execute in order — the business writes
       (e.g. ImmuDB append, future Postgres business-row insert).
    2. `final_step` executes last — the broadcast / "announce it"
       step (currently the outbox emission). Keeping it separate
       leaves the broadcast adapter swappable (PG outbox today,
       NoSQL outbox tomorrow) without touching the business pipeline."""

    def __init__(
        self,
        *,
        transaction_steps: list[SagaStep[None]],
        final_step: OutboxSagaStep,
    ) -> None:
        if not transaction_steps:
            raise ValueError("SagaCoordinator requires at least one transaction step")

        self._transaction_steps: list[SagaStep[None]] = list(transaction_steps)
        self._final_step: OutboxSagaStep = final_step

    async def run_transaction(self) -> int:
        completed_steps: list[SagaStep[Any]] = []

        try:
            for single_step in self._transaction_steps:
                await self._run_transaction_step(single_step, completed_steps)

            result = await self._run_final_step(completed_steps)
            completed_steps.append(self._final_step)
            return result
        except Exception:
            for step in reversed(completed_steps):
                await self._run_compensation(step)
            raise

    async def _run_transaction_step(
        self,
        single_step: SagaStep[None],
        completed_steps: list[SagaStep[Any]],
    ) -> None:
        try:
            logger.info("SAGA forward (transaction): %s", single_step.name)
            await single_step.forward()
            completed_steps.append(single_step)
        except Exception as forward_exc:
            logger.warning(
                "SAGA forward failed at transaction step '%s': %s; running %d compensation(s)",
                single_step.name,
                forward_exc,
                len(completed_steps),
            )
            raise

    async def _run_final_step(self, completed_steps: list[SagaStep[Any]]) -> int:
        try:
            logger.info("SAGA forward (final): %s", self._final_step.name)
            latest_sequence = await self._final_step.forward()

            return latest_sequence
        except Exception as forward_exc:
            logger.warning(
                "SAGA final step '%s' failed: %s; rolling back %d transaction step(s)",
                self._final_step.name,
                forward_exc,
                len(completed_steps),
            )
            raise

    async def _run_compensation(self, completed_step: SagaStep[Any]) -> None:
        try:
            logger.info("SAGA compensate: %s", completed_step.name)
            await completed_step.compensate()
        except Exception as compensation_exc:
            logger.critical(
                "SAGA compensation failed for step '%s'; orphan state likely",
                completed_step.name,
                exc_info=compensation_exc,
            )

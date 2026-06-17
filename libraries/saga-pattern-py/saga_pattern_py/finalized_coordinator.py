import logging
from typing import Any, Generic, TypeVar

from .saga_step import SagaStep

logger = logging.getLogger(__name__)

TFinal = TypeVar("TFinal")


class FinalizedSagaCoordinator(Generic[TFinal]):
    """Linear SAGA orchestrator with a distinguished final step.

    Two-phase run:
      1. `transaction_steps` execute in order (the business writes).
      2. `final_step` executes last (e.g. the broadcast / "announce it"),
         and its forward result is returned from `run_transaction()`.

    If any forward fails, the already-completed steps — final step included
    if it had succeeded — are compensated in reverse order and the original
    exception is re-raised. A compensation that itself fails is logged at
    CRITICAL (orphan state) but does not stop the remaining compensations.
    """

    def __init__(
        self,
        *,
        transaction_steps: list[SagaStep[Any]],
        final_step: SagaStep[TFinal],
    ) -> None:
        if not transaction_steps:
            raise ValueError("FinalizedSagaCoordinator requires at least one transaction step")
        self._transaction_steps: list[SagaStep[Any]] = list(transaction_steps)
        self._final_step: SagaStep[TFinal] = final_step

    async def run_transaction(self) -> TFinal:
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
        single_step: SagaStep[Any],
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

    async def _run_final_step(self, completed_steps: list[SagaStep[Any]]) -> TFinal:
        try:
            logger.info("SAGA forward (final): %s", self._final_step.name)
            return await self._final_step.forward()
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

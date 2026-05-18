import logging

from .saga_step import SagaStep

logger = logging.getLogger(__name__)


class SagaCoordinator:
    """Linear SAGA orchestrator with a distinguished final step.

    Two-phase run:
    1. `transaction_steps` execute in order — the business writes
       (e.g. ImmuDB append, future Postgres business-row insert).
    2. `final_step` executes last — the broadcast / "announce it"
       step (currently the outbox emission). Keeping it separate
       leaves the broadcast adapter swappable (PG outbox today,
       NoSQL outbox tomorrow) without touching the business pipeline.

    Compensation rules:
    - A transaction step's `forward()` failure runs `compensate()`
      on already-completed transaction steps in reverse order.
    - The final step's `forward()` failure runs `compensate()` on
      ALL transaction steps in reverse order (no consumer ever saw
      the announcement, so transaction state is rolled back).
    - The final step is never compensated — by definition no later
      step exists to fail after it.
    - Compensation errors are logged at CRITICAL (alertable per
      architecture.md L677) and do NOT interrupt remaining
      compensations: best-effort cleanup."""

    def __init__(
        self,
        *,
        transaction_steps: list[SagaStep],
        final_step: SagaStep,
    ) -> None:
        if not transaction_steps:
            raise ValueError("SagaCoordinator requires at least one transaction step")
        self._transaction_steps: list[SagaStep] = list(transaction_steps)
        self._final_step: SagaStep = final_step

    async def run_transaction(self) -> None:
        completed_steps: list[SagaStep] = []

        for single_step in self._transaction_steps:
            await self._run_transaction_step(single_step, completed_steps)

        await self._run_final_step(completed_steps)

    async def _run_transaction_step(
        self,
        single_step: SagaStep,
        completed_steps: list[SagaStep],
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
            await self._run_compensations(completed_steps)
            raise

    async def _run_final_step(self, completed_steps: list[SagaStep]) -> None:
        try:
            logger.info("SAGA forward (final): %s", self._final_step.name)
            await self._final_step.forward()
        except Exception as forward_exc:
            logger.warning(
                "SAGA final step '%s' failed: %s; rolling back %d transaction step(s)",
                self._final_step.name,
                forward_exc,
                len(completed_steps),
            )
            await self._run_compensations(completed_steps)
            raise

    async def _run_compensations(self, completed_steps: list[SagaStep]) -> None:
        for step in reversed(completed_steps):
            try:
                logger.info("SAGA compensate: %s", step.name)
                await step.compensate()
            except Exception as compensation_exc:
                logger.critical(
                    "SAGA compensation failed for step '%s'; orphan state likely",
                    step.name,
                    exc_info=compensation_exc,
                )

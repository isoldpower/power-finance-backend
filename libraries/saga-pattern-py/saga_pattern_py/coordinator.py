import logging
from typing import Any

from .saga_step import SagaStep

logger = logging.getLogger(__name__)


class SagaCoordinator:
    """Generic linear SAGA orchestrator. Runs `steps` forward in order.
    If any `forward()` raises, the already completed steps are compensated"""

    def __init__(self, steps: list[SagaStep[Any]]) -> None:
        if not steps:
            raise ValueError("SagaCoordinator requires at least one step")
        self._steps: list[SagaStep[Any]] = list(steps)

    async def run(self) -> list[Any]:
        completed: list[SagaStep[Any]] = []
        results: list[Any] = []
        try:
            for step in self._steps:
                logger.info("SAGA forward: %s", step.name)
                results.append(await step.forward())
                completed.append(step)
            return results
        except Exception as forward_exc:
            logger.warning(
                "SAGA forward failed at step '%s': %s; running %d compensation(s)",
                completed[-1].name if completed else "<first>",
                forward_exc,
                len(completed),
            )
            for step in reversed(completed):
                await self._compensate(step)
            raise

    async def _compensate(self, step: SagaStep[Any]) -> None:
        try:
            logger.info("SAGA compensate: %s", step.name)
            await step.compensate()
        except Exception as compensation_exc:
            logger.critical(
                "SAGA compensation failed for step '%s'; orphan state likely",
                step.name,
                exc_info=compensation_exc,
            )

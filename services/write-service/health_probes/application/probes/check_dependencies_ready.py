from health_probes.infrastructure.checkers import PostgresHealthChecker

from ..dtos import ReadinessReportDTO
from .base_probe import BaseProbe


class CheckDependenciesReady(BaseProbe):
    def __init__(self) -> None:
        super().__init__(
            {
                "postgres": PostgresHealthChecker(),
            }
        )

    async def handle(self) -> ReadinessReportDTO:
        try:
            checks = await self._run_checks()
            checks_status = self._aggregate_status(checks)

            return ReadinessReportDTO(status=checks_status, checks=checks)
        except Exception as e:
            status = self._get_degraded_status()

            return ReadinessReportDTO(status=status, checks={"internal": str(e)})

from health_probes.infrastructure.checkers import (
    MigrationsHealthChecker,
    PostgresHealthChecker,
)

from ..dtos import StartupReportDTO
from .base_probe import BaseProbe


class CheckApplicationStarted(BaseProbe):
    def __init__(self) -> None:
        super().__init__(
            {
                "postgres": PostgresHealthChecker(),
                "migrations": MigrationsHealthChecker(),
            }
        )

    async def handle(self) -> StartupReportDTO:
        try:
            checks = await self._run_checks()
            checks_status = self._aggregate_status(checks)

            return StartupReportDTO(status=checks_status, checks=checks)
        except Exception:
            status = self._get_degraded_status()

            return StartupReportDTO(status=status, checks={})

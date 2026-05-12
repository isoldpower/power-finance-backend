from health_probes.infrastructure.checkers import (
    MigrationsHealthChecker,
    PostgresHealthChecker,
)

from ..dtos import StartupReportDTO
from .base_probe import BaseProbe


class CheckApplicationStarted(BaseProbe):
    """Startup probe: "is this process finished initializing?". Kubernetes
    polls this until `ok`, then begins polling readiness; failures here
    don't terminate the pod (unlike liveness) but delay it being considered
    started.

    Includes `migrations` so a deploy that ships unapplied schema changes
    won't accept traffic until the migration step has completed.
    """

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

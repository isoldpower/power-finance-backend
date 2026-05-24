import asyncio

from health_probes.domain.entities import ProbeStatus

from ..interfaces import ServiceHealthChecker


class BaseProbe:
    _checkers: dict[str, ServiceHealthChecker]

    def __init__(self, checkers: dict[str, ServiceHealthChecker]):
        self._checkers = checkers

    async def _run_checks(self) -> dict[str, str]:
        names = list(self._checkers.keys())
        results = await asyncio.gather(
            *(checker.health_status() for checker in self._checkers.values()),
            return_exceptions=True,
        )

        return {
            name: result if isinstance(result, str) else f"Error during health check. {result!s}"
            for name, result in zip(names, results, strict=False)
        }

    @staticmethod
    def _aggregate_status(checks: dict[str, str]) -> str:
        all_ok = all(status == ProbeStatus.OK.value for status in checks.values())

        return ProbeStatus.OK.value if all_ok else ProbeStatus.DEGRADED.value

    @staticmethod
    def _get_degraded_status() -> str:
        return ProbeStatus.DEGRADED.value

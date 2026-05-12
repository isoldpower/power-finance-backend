from dataclasses import dataclass


@dataclass(frozen=True)
class ReadinessReportDTO:
    """Aggregated outcome of the readiness probe. `status` is the overall
    verdict (`ok` / `degraded`); `checks` maps each dependency name to its
    individual status string."""

    status: str
    checks: dict[str, str]

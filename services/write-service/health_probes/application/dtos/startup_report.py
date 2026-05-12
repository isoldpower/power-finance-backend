from dataclasses import dataclass


@dataclass(frozen=True)
class StartupReportDTO:
    """Aggregated outcome of the startup probe. Same shape as
    `ReadinessReportDTO` but conceptually a different signal: Kubernetes
    polls this until it reports `ok`, then begins polling readiness."""

    status: str
    checks: dict[str, str]

from dataclasses import dataclass


@dataclass(frozen=True)
class StartupReportDTO:
    """Aggregated startup-probe outcome. Same shape as ReadinessReportDTO but a
    distinct signal: polled until `ok`, then readiness takes over."""

    status: str
    checks: dict[str, str]

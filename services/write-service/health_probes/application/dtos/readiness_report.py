from dataclasses import dataclass


@dataclass(frozen=True)
class ReadinessReportDTO:
    """Aggregated readiness-probe outcome: `status` is the overall verdict,
    `checks` maps each dependency name to its status string."""

    status: str
    checks: dict[str, str]

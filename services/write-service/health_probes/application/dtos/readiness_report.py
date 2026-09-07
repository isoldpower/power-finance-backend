from dataclasses import dataclass


@dataclass(frozen=True)
class ReadinessReportDTO:
    status: str
    checks: dict[str, str]

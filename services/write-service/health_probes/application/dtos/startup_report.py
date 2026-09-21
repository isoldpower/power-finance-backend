from dataclasses import dataclass


@dataclass(frozen=True)
class StartupReportDTO:
    status: str
    checks: dict[str, str]

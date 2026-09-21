from dataclasses import dataclass


@dataclass(frozen=True)
class LivenessReportDTO:
    status: str

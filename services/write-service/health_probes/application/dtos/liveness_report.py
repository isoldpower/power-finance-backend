from dataclasses import dataclass


@dataclass(frozen=True)
class LivenessReportDTO:
    """Aggregated outcome of the liveness probe. `status` is the overall
    verdict (`ok` / `degraded`);"""

    status: str

from health_probes.application.dtos import (
    LivenessReportDTO,
    ReadinessReportDTO,
    StartupReportDTO,
)
from health_probes.domain.entities import ProbeStatus


class HealthCheckPresenter:
    """Serializes probe DTOs into the JSON shape returned to Kubernetes /
    Kong. Kept thin — DTOs already carry everything the response needs."""

    @staticmethod
    def present_degraded(exception: Exception) -> dict:
        return {
            "status": ProbeStatus.DEGRADED.value,
            "error": str(exception),
        }

    @staticmethod
    def present_liveness(report: LivenessReportDTO) -> dict:
        return {
            "status": report.status,
        }

    @staticmethod
    def present_readiness(report: ReadinessReportDTO) -> dict:
        return {
            "status": report.status,
            "checks": report.checks,
        }

    @staticmethod
    def present_startup(report: StartupReportDTO) -> dict:
        return {
            "status": report.status,
            "checks": report.checks,
        }

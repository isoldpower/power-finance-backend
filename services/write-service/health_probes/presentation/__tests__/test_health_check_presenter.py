from django.test import SimpleTestCase

from health_probes.application.dtos import (
    LivenessReportDTO,
    ReadinessReportDTO,
    StartupReportDTO,
)
from health_probes.domain.entities import ProbeStatus
from health_probes.presentation.http.presenters import HealthCheckPresenter


class HealthCheckPresenterTests(SimpleTestCase):
    def test_present_liveness_returns_status_only(self) -> None:
        report = LivenessReportDTO(status=ProbeStatus.OK.value)

        self.assertEqual(
            HealthCheckPresenter.present_liveness(report),
            {"status": "ok"},
        )

    def test_present_readiness_passes_through_checks(self) -> None:
        report = ReadinessReportDTO(
            status=ProbeStatus.OK.value,
            checks={"postgres": "ok"},
        )

        self.assertEqual(
            HealthCheckPresenter.present_readiness(report),
            {"status": "ok", "checks": {"postgres": "ok"}},
        )

    def test_present_startup_includes_per_check_diagnostics(self) -> None:
        report = StartupReportDTO(
            status=ProbeStatus.DEGRADED.value,
            checks={
                "postgres": "ok",
                "migrations": "Error checking database state. Found 1 unapplied migrations.",
            },
        )

        rendered = HealthCheckPresenter.present_startup(report)

        self.assertEqual(rendered["status"], "degraded")
        self.assertEqual(rendered["checks"]["postgres"], "ok")
        self.assertIn("unapplied migrations", rendered["checks"]["migrations"])

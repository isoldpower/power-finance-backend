from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from health_probes.application.dtos import ReadinessReportDTO, StartupReportDTO
from health_probes.domain.entities import ProbeStatus


class LivenessViewTests(TestCase):
    def test_always_returns_200_with_ok_status(self) -> None:
        response = self.client.get(reverse("health-live"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


class ReadinessViewTests(TestCase):
    def test_returns_200_when_probe_reports_ok(self) -> None:
        async def fake_handle(self):
            return ReadinessReportDTO(status=ProbeStatus.OK.value, checks={"postgres": "ok"})

        with patch(
            "health_probes.application.probes.CheckDependenciesReady.handle",
            fake_handle,
        ):
            response = self.client.get(reverse("health-ready"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"status": "ok", "checks": {"postgres": "ok"}},
        )

    def test_returns_503_when_probe_reports_degraded(self) -> None:
        async def fake_handle(self):
            return ReadinessReportDTO(
                status=ProbeStatus.DEGRADED.value,
                checks={"postgres": "Error connecting to PostgreSQL database."},
            )

        with patch(
            "health_probes.application.probes.CheckDependenciesReady.handle",
            fake_handle,
        ):
            response = self.client.get(reverse("health-ready"))

        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertEqual(body["status"], "degraded")
        self.assertIn("Error connecting", body["checks"]["postgres"])

    def test_returns_503_when_handler_raises(self) -> None:
        async def boom(self):
            raise RuntimeError("orchestration broken")

        with patch(
            "health_probes.application.probes.CheckDependenciesReady.handle",
            boom,
        ):
            response = self.client.get(reverse("health-ready"))

        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertEqual(body["status"], "degraded")
        self.assertIn("orchestration broken", body["error"])


class StartupViewTests(TestCase):
    def test_returns_200_when_probe_reports_ok(self) -> None:
        async def fake_handle(self):
            return StartupReportDTO(
                status=ProbeStatus.OK.value,
                checks={"postgres": "ok", "migrations": "ok"},
            )

        with patch(
            "health_probes.application.probes.CheckApplicationStarted.handle",
            fake_handle,
        ):
            response = self.client.get(reverse("health-startup"))

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["checks"]["migrations"], "ok")

    def test_returns_503_when_probe_reports_degraded(self) -> None:
        async def fake_handle(self):
            return StartupReportDTO(
                status=ProbeStatus.DEGRADED.value,
                checks={
                    "migrations": "Error checking database state. Found 2 unapplied migrations."
                },
            )

        with patch(
            "health_probes.application.probes.CheckApplicationStarted.handle",
            fake_handle,
        ):
            response = self.client.get(reverse("health-startup"))

        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertEqual(body["status"], "degraded")
        self.assertIn("unapplied migrations", body["checks"]["migrations"])

    def test_returns_503_when_handler_raises(self) -> None:
        async def boom(self):
            raise RuntimeError("startup orchestration broken")

        with patch(
            "health_probes.application.probes.CheckApplicationStarted.handle",
            boom,
        ):
            response = self.client.get(reverse("health-startup"))

        self.assertEqual(response.status_code, 503)
        body = response.json()
        self.assertEqual(body["status"], "degraded")
        self.assertIn("startup orchestration broken", body["error"])

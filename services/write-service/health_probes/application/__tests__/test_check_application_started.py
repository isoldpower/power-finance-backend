from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from health_probes.application.dtos import StartupReportDTO
from health_probes.application.probes import CheckApplicationStarted
from health_probes.domain.entities import ProbeStatus


class CheckApplicationStartedTests(IsolatedAsyncioTestCase):
    async def test_registers_postgres_and_migrations_checkers(self) -> None:
        probe = CheckApplicationStarted()
        self.assertIn("postgres", probe._checkers)
        self.assertIn("migrations", probe._checkers)

    async def test_returns_ok_when_postgres_and_migrations_ok(self) -> None:
        async def fake_run_checks(self):
            return {
                "postgres": ProbeStatus.OK.value,
                "migrations": ProbeStatus.OK.value,
            }

        with patch(
            "health_probes.application.probes.base_probe.BaseProbe._run_checks",
            fake_run_checks,
        ):
            probe = CheckApplicationStarted()
            report = await probe.handle()

        self.assertIsInstance(report, StartupReportDTO)
        self.assertEqual(report.status, ProbeStatus.OK.value)
        self.assertEqual(report.checks["postgres"], "ok")
        self.assertEqual(report.checks["migrations"], "ok")

    async def test_returns_degraded_when_migrations_unapplied(self) -> None:
        async def fake_run_checks(self):
            return {
                "postgres": ProbeStatus.OK.value,
                "migrations": "Error checking database state. Found 2 unapplied migrations.",
            }

        with patch(
            "health_probes.application.probes.base_probe.BaseProbe._run_checks",
            fake_run_checks,
        ):
            probe = CheckApplicationStarted()
            report = await probe.handle()

        self.assertEqual(report.status, ProbeStatus.DEGRADED.value)
        self.assertIn("unapplied migrations", report.checks["migrations"])

    async def test_returns_degraded_with_empty_checks_on_internal_error(self) -> None:
        async def boom(self):
            raise RuntimeError("orchestration broken")

        with patch(
            "health_probes.application.probes.base_probe.BaseProbe._run_checks",
            boom,
        ):
            probe = CheckApplicationStarted()
            report = await probe.handle()

        self.assertEqual(report.status, ProbeStatus.DEGRADED.value)
        self.assertEqual(report.checks, {})

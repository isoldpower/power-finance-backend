from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch

from health_probes.application.dtos import ReadinessReportDTO
from health_probes.application.probes import CheckDependenciesReady
from health_probes.domain.entities import ProbeStatus


class CheckDependenciesReadyTests(IsolatedAsyncioTestCase):
    async def test_registers_postgres_checker(self) -> None:
        probe = CheckDependenciesReady()
        self.assertIn("postgres", probe._checkers)

    async def test_returns_ok_dto_when_all_dependencies_healthy(self) -> None:
        async def fake_run_checks(self):
            return {"postgres": ProbeStatus.OK.value}

        with patch(
            "health_probes.application.probes.base_probe.BaseProbe._run_checks",
            fake_run_checks,
        ):
            probe = CheckDependenciesReady()
            report = await probe.handle()

        self.assertIsInstance(report, ReadinessReportDTO)
        self.assertEqual(report.status, ProbeStatus.OK.value)
        self.assertEqual(report.checks, {"postgres": "ok"})

    async def test_returns_degraded_dto_when_any_dependency_fails(self) -> None:
        async def fake_run_checks(self):
            return {"postgres": "Error connecting to PostgreSQL database."}

        with patch(
            "health_probes.application.probes.base_probe.BaseProbe._run_checks",
            fake_run_checks,
        ):
            probe = CheckDependenciesReady()
            report = await probe.handle()

        self.assertEqual(report.status, ProbeStatus.DEGRADED.value)
        self.assertEqual(
            report.checks,
            {"postgres": "Error connecting to PostgreSQL database."},
        )

    async def test_captures_internal_error_in_dto(self) -> None:
        async def boom(self):
            raise RuntimeError("orchestration broken")

        with patch(
            "health_probes.application.probes.base_probe.BaseProbe._run_checks",
            boom,
        ):
            probe = CheckDependenciesReady()
            report = await probe.handle()

        self.assertEqual(report.status, ProbeStatus.DEGRADED.value)
        self.assertEqual(report.checks, {"internal": "orchestration broken"})

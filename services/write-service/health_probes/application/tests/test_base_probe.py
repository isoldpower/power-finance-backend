from unittest import IsolatedAsyncioTestCase

from django.test import SimpleTestCase

from health_probes.application.interfaces import ServiceHealthChecker
from health_probes.application.probes.base_probe import BaseProbe
from health_probes.domain.entities import ProbeStatus


class _FakeChecker(ServiceHealthChecker):
    def __init__(self, result: str) -> None:
        self._result = result

    async def health_status(self) -> str:
        return self._result


class _RaisingChecker(ServiceHealthChecker):
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def health_status(self) -> str:
        raise self._exc


class AggregateStatusTests(SimpleTestCase):
    def test_returns_ok_when_every_check_ok(self) -> None:
        checks = {"a": "ok", "b": "ok"}
        self.assertEqual(BaseProbe._aggregate_status(checks), ProbeStatus.OK.value)

    def test_returns_degraded_when_any_check_not_ok(self) -> None:
        checks = {"a": "ok", "b": "down"}
        self.assertEqual(BaseProbe._aggregate_status(checks), ProbeStatus.DEGRADED.value)

    def test_returns_ok_for_empty_check_map(self) -> None:
        self.assertEqual(BaseProbe._aggregate_status({}), ProbeStatus.OK.value)


class RunChecksTests(IsolatedAsyncioTestCase):
    async def test_runs_all_checkers_concurrently_and_collects_results(self) -> None:
        probe = BaseProbe(
            {
                "postgres": _FakeChecker(ProbeStatus.OK.value),
                "redis": _FakeChecker("Error connecting to Redis."),
            }
        )

        results = await probe._run_checks()

        self.assertEqual(
            results,
            {
                "postgres": "ok",
                "redis": "Error connecting to Redis.",
            },
        )

    async def test_captured_exception_becomes_error_string(self) -> None:
        probe = BaseProbe(
            {
                "postgres": _FakeChecker(ProbeStatus.OK.value),
                "redis": _RaisingChecker(RuntimeError("boom")),
            }
        )

        results = await probe._run_checks()

        self.assertEqual(results["postgres"], "ok")
        self.assertIn("Error during health check.", results["redis"])
        self.assertIn("boom", results["redis"])

    async def test_returns_empty_when_no_checkers_registered(self) -> None:
        probe = BaseProbe({})

        self.assertEqual(await probe._run_checks(), {})

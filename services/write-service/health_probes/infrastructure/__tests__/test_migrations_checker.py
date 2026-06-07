from unittest import IsolatedAsyncioTestCase
from unittest.mock import MagicMock, patch

from health_probes.domain.entities import ProbeStatus
from health_probes.infrastructure.checkers import MigrationsHealthChecker


def _executor_with_plan_size(plan_size: int) -> MagicMock:
    executor = MagicMock()
    executor.loader.graph.leaf_nodes.return_value = ["leaf-a", "leaf-b"]
    executor.migration_plan.return_value = ["m"] * plan_size
    return executor


class MigrationsHealthCheckerTests(IsolatedAsyncioTestCase):
    async def test_returns_ok_when_no_unapplied_migrations(self) -> None:
        executor = _executor_with_plan_size(0)
        fake_connections = {"default": MagicMock()}

        with (
            patch(
                "health_probes.infrastructure.checkers.migrations_checker.connections",
                fake_connections,
            ),
            patch(
                "health_probes.infrastructure.checkers.migrations_checker.MigrationExecutor",
                return_value=executor,
            ),
        ):
            result = await MigrationsHealthChecker().health_status()

        self.assertEqual(result, ProbeStatus.OK.value)

    async def test_returns_error_with_count_when_migrations_outstanding(self) -> None:
        executor = _executor_with_plan_size(3)
        fake_connections = {"default": MagicMock()}

        with (
            patch(
                "health_probes.infrastructure.checkers.migrations_checker.connections",
                fake_connections,
            ),
            patch(
                "health_probes.infrastructure.checkers.migrations_checker.MigrationExecutor",
                return_value=executor,
            ),
        ):
            result = await MigrationsHealthChecker().health_status()

        self.assertIn("Found 3 unapplied migrations", result)

    async def test_returns_error_string_when_executor_raises(self) -> None:
        fake_connections = {"default": MagicMock()}

        with (
            patch(
                "health_probes.infrastructure.checkers.migrations_checker.connections",
                fake_connections,
            ),
            patch(
                "health_probes.infrastructure.checkers.migrations_checker.MigrationExecutor",
                side_effect=RuntimeError("graph corrupt"),
            ),
        ):
            result = await MigrationsHealthChecker().health_status()

        self.assertIn("Error checking database state", result)
        self.assertIn("graph corrupt", result)

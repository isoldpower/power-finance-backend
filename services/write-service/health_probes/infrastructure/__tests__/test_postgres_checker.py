from unittest import IsolatedAsyncioTestCase
from unittest.mock import MagicMock, patch

from health_probes.domain.entities import ProbeStatus
from health_probes.infrastructure.checkers import PostgresHealthChecker


class _FakeConnection:
    def __init__(self, fetchone_value, raise_on_execute: Exception | None = None) -> None:
        self._fetchone_value = fetchone_value
        self._raise_on_execute = raise_on_execute

    def cursor(self):
        cursor = MagicMock()
        cursor.__enter__.return_value = cursor
        cursor.__exit__.return_value = False
        if self._raise_on_execute is not None:
            cursor.execute.side_effect = self._raise_on_execute
        cursor.fetchone.return_value = self._fetchone_value
        return cursor


class PostgresHealthCheckerTests(IsolatedAsyncioTestCase):
    async def test_returns_ok_when_select_1_succeeds(self) -> None:
        fake_connections = {"default": _FakeConnection(fetchone_value=(1,))}

        with patch(
            "health_probes.infrastructure.checkers.postgres_checker.connections", fake_connections
        ):
            result = await PostgresHealthChecker().health_status()

        self.assertEqual(result, ProbeStatus.OK.value)

    async def test_returns_error_when_fetchone_returns_none(self) -> None:
        fake_connections = {"default": _FakeConnection(fetchone_value=None)}

        with patch(
            "health_probes.infrastructure.checkers.postgres_checker.connections", fake_connections
        ):
            result = await PostgresHealthChecker().health_status()

        self.assertIn("Corrupted response from database", result)

    async def test_returns_error_string_when_cursor_raises(self) -> None:
        fake_connections = {
            "default": _FakeConnection(
                fetchone_value=(1,),
                raise_on_execute=ConnectionError("network unreachable"),
            )
        }

        with patch(
            "health_probes.infrastructure.checkers.postgres_checker.connections", fake_connections
        ):
            result = await PostgresHealthChecker().health_status()

        self.assertIn("Error connecting to PostgreSQL database", result)
        self.assertIn("network unreachable", result)

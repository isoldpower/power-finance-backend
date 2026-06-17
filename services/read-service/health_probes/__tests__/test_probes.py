from data_read_core.shared.health_guard import HealthProbe

from ..probes import ProbeStatus, check_dependencies_ready


class FakeProbe(HealthProbe):
    def __init__(self, name: str, healthy: bool) -> None:
        super().__init__()
        self._name = name
        self._healthy = healthy

    @property
    def name(self) -> str:
        return self._name

    async def is_healthy(self) -> bool:
        return self._healthy


async def test_readiness_ok_when_all_probes_healthy():
    checks_status, checks = await check_dependencies_ready(
        probes=[FakeProbe("postgres", True), FakeProbe("redis", True)],
    )

    assert checks_status == ProbeStatus.OK.value
    assert checks == {"postgres": "ok", "redis": "ok"}


async def test_readiness_degraded_when_any_probe_unhealthy():
    checks_status, checks = await check_dependencies_ready(
        probes=[FakeProbe("postgres", True), FakeProbe("elasticsearch", False)],
    )

    assert checks_status == ProbeStatus.DEGRADED.value
    assert checks["postgres"] == "ok"
    assert "elasticsearch" in checks["elasticsearch"]

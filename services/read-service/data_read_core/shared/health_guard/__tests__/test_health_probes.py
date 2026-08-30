"""The probes this service wires into the shared health guard."""

from data_read_core.shared.health_guard import (
    ElasticsearchHealthProbe,
    RedisHealthProbe,
)
from data_read_core.shared.health_guard import (
    elasticsearch_health_probe as es_probe_module,
)
from data_read_core.shared.health_guard import (
    redis_health_probe as redis_probe_module,
)


class _FakePingClient:
    def __init__(self, *, result=True, raises=None):
        self._result = result
        self._raises = raises

    async def ping(self):
        if self._raises is not None:
            raise self._raises
        return self._result


async def test_elasticsearch_probe_healthy_when_ping_ok(monkeypatch):
    monkeypatch.setattr(es_probe_module, "get_elasticsearch", lambda: _FakePingClient(result=True))
    assert await ElasticsearchHealthProbe().is_healthy() is True


async def test_elasticsearch_probe_unhealthy_on_connectivity_error(monkeypatch):
    monkeypatch.setattr(
        es_probe_module, "get_elasticsearch", lambda: _FakePingClient(raises=OSError("no route"))
    )
    assert await ElasticsearchHealthProbe().is_healthy() is False


async def test_redis_probe_healthy_when_ping_ok(monkeypatch):
    monkeypatch.setattr(redis_probe_module, "get_redis", lambda: _FakePingClient(result=True))
    assert await RedisHealthProbe().is_healthy() is True


async def test_redis_probe_unhealthy_on_connectivity_error(monkeypatch):
    monkeypatch.setattr(
        redis_probe_module, "get_redis", lambda: _FakePingClient(raises=OSError("down"))
    )
    assert await RedisHealthProbe().is_healthy() is False

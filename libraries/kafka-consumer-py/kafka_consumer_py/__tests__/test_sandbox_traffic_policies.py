"""Who processes a sandbox's events: its own consumer, or the baseline as fallback."""

from kafka_consumer_py import (
    BaselineFallbackTrafficPolicy,
    StrictSandboxTrafficPolicy,
    build_sandbox_traffic_policy,
)


class _FakeRegistry:
    def __init__(self, running_sandboxes: set[str]) -> None:
        self._running_sandboxes = running_sandboxes
        self.asked = []

    async def has_consumer_for(self, sandbox_id: str) -> bool:
        self.asked.append(sandbox_id)

        return sandbox_id in self._running_sandboxes


class _Config:
    bootstrap_servers = "localhost:9092"
    group_id = "read-service.write-consumer"


async def test_a_sandbox_takes_only_its_own_traffic():
    policy = StrictSandboxTrafficPolicy("nikita")

    assert await policy.is_owned_traffic("nikita") is True
    assert await policy.is_owned_traffic("alice") is False
    assert await policy.is_owned_traffic(None) is False


async def test_the_baseline_always_takes_untagged_traffic():
    policy = BaselineFallbackTrafficPolicy(_FakeRegistry(set()))

    assert await policy.is_owned_traffic(None) is True
    assert await policy.is_owned_traffic("") is True


async def test_the_baseline_leaves_traffic_to_a_sandbox_running_this_service():
    policy = BaselineFallbackTrafficPolicy(_FakeRegistry({"nikita"}))

    assert await policy.is_owned_traffic("nikita") is False


async def test_the_baseline_covers_a_sandbox_not_running_this_service():
    registry = _FakeRegistry({"nikita"})
    policy = BaselineFallbackTrafficPolicy(registry)

    assert await policy.is_owned_traffic("alice") is True
    assert registry.asked == ["alice"]


async def test_a_sandbox_process_gets_the_strict_policy():
    policy = build_sandbox_traffic_policy(_Config(), "nikita")

    assert isinstance(policy, StrictSandboxTrafficPolicy)
    assert policy.own_sandbox_id == "nikita"


async def test_a_baseline_process_gets_the_fallback_policy():
    policy = build_sandbox_traffic_policy(_Config(), None)

    assert isinstance(policy, BaselineFallbackTrafficPolicy)
    assert policy.own_sandbox_id is None

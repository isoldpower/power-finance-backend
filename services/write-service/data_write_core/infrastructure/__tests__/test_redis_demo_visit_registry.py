from datetime import UTC, datetime, timedelta

import pytest
from redis.exceptions import RedisError

from data_write_core.infrastructure.demo import RedisDemoVisitRegistry, normalise_client_address

NOW = datetime(2026, 11, 15, 12, 0, 0, tzinfo=UTC)
HOLD_UNTIL = NOW + timedelta(hours=23, minutes=55)
CLIENT_KEY_SECRET = "a-demo-session-secret-of-at-least-32-characters"


class FakeRedis:
    def __init__(self) -> None:
        self.storage: dict[str, bytes] = {}
        self.expirations: dict[str, int] = {}
        self.raise_errors = False
        self.vanishing_reads = 0

    async def set(self, key, value, nx=False, ex=None):
        if self.raise_errors:
            raise RedisError("connection refused")
        if nx and key in self.storage:
            return None
        self.storage[key] = value.encode()
        self.expirations[key] = ex
        return True

    async def get(self, key):
        if self.raise_errors:
            raise RedisError("connection refused")
        if self.vanishing_reads:
            self.vanishing_reads -= 1
            self.storage.pop(key, None)
        return self.storage.get(key)


def _registry(redis: FakeRedis) -> RedisDemoVisitRegistry:
    return RedisDemoVisitRegistry(redis, CLIENT_KEY_SECRET, clock=lambda: NOW)  # type: ignore[arg-type]


async def test_the_first_claim_holds_the_candidate_until_the_rotation_window():
    redis = FakeRedis()

    active_identifier = await _registry(redis).claim_active_visit(
        "203.0.113.7", "dv1_first", HOLD_UNTIL
    )

    (client_key,) = redis.storage
    assert active_identifier == "dv1_first"
    assert redis.expirations[client_key] == int((HOLD_UNTIL - NOW).total_seconds())


async def test_a_later_claim_returns_the_held_visit():
    redis = FakeRedis()
    registry = _registry(redis)
    await registry.claim_active_visit("203.0.113.7", "dv1_first", HOLD_UNTIL)

    active_identifier = await registry.claim_active_visit("203.0.113.7", "dv1_second", HOLD_UNTIL)

    assert active_identifier == "dv1_first"


async def test_the_client_address_never_reaches_redis_in_clear():
    redis = FakeRedis()

    await _registry(redis).claim_active_visit("203.0.113.7", "dv1_first", HOLD_UNTIL)

    (client_key,) = redis.storage
    assert client_key.startswith("demo:client:")
    assert "203.0.113.7" not in client_key


async def test_a_replacement_overwrites_the_held_visit():
    redis = FakeRedis()
    registry = _registry(redis)
    await registry.claim_active_visit("203.0.113.7", "dv1_first", HOLD_UNTIL)

    await registry.replace_active_visit("203.0.113.7", "dv1_second", HOLD_UNTIL)

    assert await registry.claim_active_visit("203.0.113.7", "dv1_third", HOLD_UNTIL) == "dv1_second"


async def test_a_visit_that_expires_between_set_and_get_is_claimed_again():
    redis = FakeRedis()
    registry = _registry(redis)
    await registry.claim_active_visit("203.0.113.7", "dv1_first", HOLD_UNTIL)
    redis.vanishing_reads = 1

    active_identifier = await registry.claim_active_visit("203.0.113.7", "dv1_second", HOLD_UNTIL)

    assert active_identifier == "dv1_second"


async def test_an_unreachable_redis_issues_without_a_limit():
    redis = FakeRedis()
    redis.raise_errors = True
    registry = _registry(redis)

    assert await registry.claim_active_visit("203.0.113.7", "dv1_first", HOLD_UNTIL) == "dv1_first"
    await registry.replace_active_visit("203.0.113.7", "dv1_first", HOLD_UNTIL)


@pytest.mark.parametrize(
    ("first_address", "second_address"),
    [
        ("2001:db8:1:2::1", "2001:db8:1:2:ffff::9"),
        ("::ffff:203.0.113.7", "203.0.113.7"),
        (" 203.0.113.7 ", "203.0.113.7"),
    ],
)
def test_addresses_of_one_client_normalise_alike(first_address, second_address):
    assert normalise_client_address(first_address) == normalise_client_address(second_address)


def test_neighbouring_ipv6_networks_are_different_clients():
    assert normalise_client_address("2001:db8:1:2::1") != normalise_client_address(
        "2001:db8:1:3::1"
    )

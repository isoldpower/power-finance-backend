import pytest

from tests.fakes import FakeRedis


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()

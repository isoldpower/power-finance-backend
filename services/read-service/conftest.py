import pytest
from fakes import FakeRedis


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()

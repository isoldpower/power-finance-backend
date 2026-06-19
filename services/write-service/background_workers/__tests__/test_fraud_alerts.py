import asyncio
from dataclasses import dataclass

import pytest
from kafka_client_py import PoisonError

from background_workers.services.fraud_alerts import (
    SuspendedUser,
    SuspendedUserStore,
    _parse_fraud_alert,
)


@dataclass
class FakeRecord:
    key: bytes | None
    value: bytes | None
    topic: str = "fraud.alerts"
    partition: int = 0
    offset: int = 0
    headers: tuple = ()


class FakeRedis:
    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}

    async def hset(self, key: str, field: str, value: str) -> None:
        self.hashes.setdefault(key, {})[field] = value


def test_parse_uses_key_as_clerk_id_and_value_as_reason():
    record = FakeRecord(key=b"user_abc", value=b"FRAUD clerk=user_abc score=8.0")

    user = _parse_fraud_alert(record)

    assert user.clerk_id == "user_abc"
    assert user.reason == "FRAUD clerk=user_abc score=8.0"


def test_parse_missing_key_is_poison():
    with pytest.raises(PoisonError):
        _parse_fraud_alert(FakeRecord(key=None, value=b"FRAUD ..."))


def test_parse_empty_key_is_poison():
    with pytest.raises(PoisonError):
        _parse_fraud_alert(FakeRecord(key=b"", value=b"FRAUD ..."))


def test_parse_tolerates_empty_value():
    user = _parse_fraud_alert(FakeRecord(key=b"user_abc", value=None))

    assert user.clerk_id == "user_abc"
    assert user.reason == ""


def test_store_records_suspended_user_in_hash():
    fake = FakeRedis()
    store = SuspendedUserStore(fake)

    asyncio.run(store.suspend(SuspendedUser(clerk_id="user_abc", reason="FRAUD score=8.0")))

    assert fake.hashes[SuspendedUserStore.SUSPENDED_USERS_KEY] == {"user_abc": "FRAUD score=8.0"}

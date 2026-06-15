import pytest
from rest_framework import status

from data_read_core.shared.read_at_least import (
    ReadModelNotCaughtUp,
    ensure_es_read_at_least,
    record_applied_seq,
    record_es_applied_seq,
)


class _FakeUser:
    def __init__(self, user_id: int) -> None:
        self.id = user_id


class _FakeRequest:
    def __init__(self, user_id: int, headers: dict[str, str] | None = None) -> None:
        self.user = _FakeUser(user_id)
        self.headers = headers or {}


async def test_no_header_is_a_noop():
    await ensure_es_read_at_least(_FakeRequest(7))


@pytest.mark.django_db(transaction=True)
async def test_caught_up_passes():
    await record_es_applied_seq(user_id=7, outbox_seq=100)

    await ensure_es_read_at_least(_FakeRequest(7, {"Read-At-Least": "100"}))


@pytest.mark.django_db(transaction=True)
async def test_behind_raises_507():
    await record_es_applied_seq(user_id=7, outbox_seq=99)

    with pytest.raises(ReadModelNotCaughtUp) as exc_info:
        await ensure_es_read_at_least(_FakeRequest(7, {"Read-At-Least": "100"}))

    assert exc_info.value.status_code == status.HTTP_507_INSUFFICIENT_STORAGE


@pytest.mark.django_db(transaction=True)
async def test_postgres_seq_does_not_satisfy_es_gate():
    # Postgres projection is ahead, but ES has applied nothing — the ES gate
    # must read its own table and still reject.
    await record_applied_seq(user_id=7, outbox_seq=100)

    with pytest.raises(ReadModelNotCaughtUp):
        await ensure_es_read_at_least(_FakeRequest(7, {"Read-At-Least": "100"}))

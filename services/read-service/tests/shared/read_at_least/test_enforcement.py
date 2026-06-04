import pytest
from data_read_core.shared.read_at_least import (
    ReadModelNotCaughtUp,
    ensure_read_at_least,
    record_applied_seq,
)
from rest_framework import status


class _FakeUser:
    def __init__(self, user_id: int) -> None:
        self.id = user_id


class _FakeRequest:
    def __init__(self, user_id: int, headers: dict[str, str] | None = None) -> None:
        self.user = _FakeUser(user_id)
        self.headers = headers or {}


async def test_no_header_is_a_noop():
    # No DB access expected — the gate short-circuits before reading.
    await ensure_read_at_least(_FakeRequest(7))


async def test_unparseable_header_is_a_noop():
    await ensure_read_at_least(_FakeRequest(7, {"Read-At-Least": "garbage"}))


@pytest.mark.django_db(transaction=True)
async def test_caught_up_passes():
    await record_applied_seq(user_id=7, outbox_seq=100)

    await ensure_read_at_least(_FakeRequest(7, {"Read-At-Least": "100"}))


@pytest.mark.django_db(transaction=True)
async def test_behind_raises_507():
    await record_applied_seq(user_id=7, outbox_seq=99)

    with pytest.raises(ReadModelNotCaughtUp) as exc_info:
        await ensure_read_at_least(_FakeRequest(7, {"Read-At-Least": "100"}))

    assert exc_info.value.status_code == status.HTTP_507_INSUFFICIENT_STORAGE


@pytest.mark.django_db(transaction=True)
async def test_nothing_applied_yet_raises_507():
    with pytest.raises(ReadModelNotCaughtUp):
        await ensure_read_at_least(_FakeRequest(7, {"Read-At-Least": "1"}))


@pytest.mark.django_db(transaction=True)
async def test_scope_is_per_user():
    await record_applied_seq(user_id=7, outbox_seq=100)

    # User 9 has no applied seq, so their own RAL is unmet even though user 7 is ahead.
    with pytest.raises(ReadModelNotCaughtUp):
        await ensure_read_at_least(_FakeRequest(9, {"Read-At-Least": "100"}))

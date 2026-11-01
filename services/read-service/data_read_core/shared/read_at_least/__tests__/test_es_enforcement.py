import pytest
from django.utils import timezone
from rest_framework import status

from data_read_core.shared.read_at_least import (
    EsPendingOutboxSeq,
    ReadModelNotCaughtUp,
    clear_es_pending_seqs_failed_before,
    ensure_es_read_at_least,
    record_applied_seq,
    record_es_applied_seq,
    record_es_pending_seq,
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
    await record_applied_seq(user_id=7, outbox_seq=100)

    with pytest.raises(ReadModelNotCaughtUp):
        await ensure_es_read_at_least(_FakeRequest(7, {"Read-At-Least": "100"}))


@pytest.mark.django_db(transaction=True)
async def test_a_held_seq_keeps_the_gate_closed_despite_later_writes():
    await record_es_applied_seq(user_id=7, outbox_seq=120)
    await record_es_pending_seq(user_id=7, outbox_seq=110, event_id="evt-dead")

    with pytest.raises(ReadModelNotCaughtUp):
        await ensure_es_read_at_least(_FakeRequest(7, {"Read-At-Least": "120"}))


@pytest.mark.django_db(transaction=True)
async def test_a_held_seq_above_the_required_one_does_not_block():
    await record_es_applied_seq(user_id=7, outbox_seq=120)
    await record_es_pending_seq(user_id=7, outbox_seq=115, event_id="evt-dead")

    await ensure_es_read_at_least(_FakeRequest(7, {"Read-At-Least": "100"}))


@pytest.mark.django_db(transaction=True)
async def test_backfill_release_keeps_holds_recorded_after_it_started():
    await record_es_pending_seq(user_id=7, outbox_seq=110, event_id="evt-old")
    started_at = timezone.now()
    await record_es_pending_seq(user_id=7, outbox_seq=111, event_id="evt-new")

    released = await clear_es_pending_seqs_failed_before(started_at)

    assert released == 1
    remaining = EsPendingOutboxSeq.objects.values_list("outbox_seq", flat=True)
    assert [seq async for seq in remaining] == [111]

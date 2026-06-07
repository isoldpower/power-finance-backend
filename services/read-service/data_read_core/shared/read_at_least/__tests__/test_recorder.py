import pytest

from data_read_core.shared.read_at_least import (
    AppliedOutboxSeq,
    DjangoAppliedSeqReader,
    record_applied_seq,
)


@pytest.mark.django_db(transaction=True)
async def test_record_creates_row_for_new_user():
    await record_applied_seq(user_id=7, outbox_seq=42)

    applied = await DjangoAppliedSeqReader().applied_seq("7")
    assert applied == 42


@pytest.mark.django_db(transaction=True)
async def test_record_advances_to_higher_seq():
    await record_applied_seq(user_id=7, outbox_seq=42)
    await record_applied_seq(user_id=7, outbox_seq=100)

    assert await DjangoAppliedSeqReader().applied_seq("7") == 100


@pytest.mark.django_db(transaction=True)
async def test_record_never_moves_backwards():
    await record_applied_seq(user_id=7, outbox_seq=100)
    await record_applied_seq(user_id=7, outbox_seq=42)

    assert await DjangoAppliedSeqReader().applied_seq("7") == 100


@pytest.mark.django_db(transaction=True)
async def test_record_isolates_users():
    await record_applied_seq(user_id=7, outbox_seq=100)
    await record_applied_seq(user_id=9, outbox_seq=5)

    reader = DjangoAppliedSeqReader()
    assert await reader.applied_seq("7") == 100
    assert await reader.applied_seq("9") == 5


@pytest.mark.django_db(transaction=True)
async def test_reader_returns_none_for_unknown_user():
    assert await DjangoAppliedSeqReader().applied_seq("123") is None


@pytest.mark.django_db(transaction=True)
async def test_record_persists_single_row_per_user():
    await record_applied_seq(user_id=7, outbox_seq=1)
    await record_applied_seq(user_id=7, outbox_seq=2)

    assert await AppliedOutboxSeq.objects.filter(user_id=7).acount() == 1

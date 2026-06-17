import pytest

from data_read_core.shared.read_at_least import (
    DjangoAppliedSeqReader,
    DjangoEsAppliedSeqReader,
    EsAppliedOutboxSeq,
    record_applied_seq,
    record_es_applied_seq,
)


@pytest.mark.django_db(transaction=True)
async def test_record_creates_row_for_new_user():
    await record_es_applied_seq(user_id=7, outbox_seq=42)

    assert await DjangoEsAppliedSeqReader().applied_seq("7") == 42


@pytest.mark.django_db(transaction=True)
async def test_record_advances_and_never_moves_backwards():
    await record_es_applied_seq(user_id=7, outbox_seq=100)
    await record_es_applied_seq(user_id=7, outbox_seq=42)

    assert await DjangoEsAppliedSeqReader().applied_seq("7") == 100


@pytest.mark.django_db(transaction=True)
async def test_reader_returns_none_for_unknown_user():
    assert await DjangoEsAppliedSeqReader().applied_seq("123") is None


@pytest.mark.django_db(transaction=True)
async def test_es_seq_is_independent_of_postgres_seq():
    await record_applied_seq(user_id=7, outbox_seq=100)
    await record_es_applied_seq(user_id=7, outbox_seq=20)

    assert await DjangoAppliedSeqReader().applied_seq("7") == 100
    assert await DjangoEsAppliedSeqReader().applied_seq("7") == 20


@pytest.mark.django_db(transaction=True)
async def test_record_persists_single_row_per_user():
    await record_es_applied_seq(user_id=7, outbox_seq=1)
    await record_es_applied_seq(user_id=7, outbox_seq=2)

    assert await EsAppliedOutboxSeq.objects.filter(user_id=7).acount() == 1

import pytest
from fakes import make_event
from kafka_consumer_py import Effect, EventMessage
from kafka_messages import NotificationsAcknowledged, WalletCreated

from data_read_core.shared.read_at_least import (
    DjangoAppliedSeqReader,
    DjangoEsAppliedSeqReader,
    record_es_applied_seq,
    record_es_pending_seq,
)
from data_read_core.write_reactions import AdvanceEsAppliedSeq, TrackEsAppliedSeq


class _RecordingEffect(Effect):
    def __init__(self) -> None:
        self.applied: list[EventMessage] = []

    async def apply(self, event: EventMessage) -> None:
        self.applied.append(event)


class _FailingEffect(Effect):
    async def apply(self, event: EventMessage) -> None:
        raise RuntimeError("elasticsearch unavailable")


@pytest.mark.django_db(transaction=True)
async def test_records_es_seq_and_runs_inner():
    inner = _RecordingEffect()
    effect = TrackEsAppliedSeq(inner, WalletCreated)

    await effect.apply(make_event(WalletCreated(user_id=7, wallet_id="w-1"), outbox_seq=55))

    assert len(inner.applied) == 1
    assert await DjangoEsAppliedSeqReader().applied_seq("7") == 55


@pytest.mark.django_db(transaction=True)
async def test_missing_outbox_seq_projects_without_recording():
    inner = _RecordingEffect()
    effect = TrackEsAppliedSeq(inner, WalletCreated)

    await effect.apply(make_event(WalletCreated(user_id=7, wallet_id="w-1"), outbox_seq=None))

    assert len(inner.applied) == 1
    assert await DjangoEsAppliedSeqReader().applied_seq("7") is None


@pytest.mark.django_db(transaction=True)
async def test_es_failure_leaves_seq_unrecorded():
    effect = TrackEsAppliedSeq(_FailingEffect(), WalletCreated)

    with pytest.raises(RuntimeError):
        await effect.apply(make_event(WalletCreated(user_id=7, wallet_id="w-1"), outbox_seq=55))

    assert await DjangoEsAppliedSeqReader().applied_seq("7") is None


@pytest.mark.django_db(transaction=True)
async def test_es_seq_is_tracked_separately_from_postgres():
    effect = TrackEsAppliedSeq(_RecordingEffect(), WalletCreated)

    await effect.apply(make_event(WalletCreated(user_id=7, wallet_id="w-1"), outbox_seq=55))

    assert await DjangoEsAppliedSeqReader().applied_seq("7") == 55
    assert await DjangoAppliedSeqReader().applied_seq("7") is None


@pytest.mark.django_db(transaction=True)
async def test_an_unindexed_event_still_carries_the_search_watermark_forward():
    await record_es_applied_seq(7, 397)

    await AdvanceEsAppliedSeq(NotificationsAcknowledged).apply(
        make_event(NotificationsAcknowledged(user_id=7), outbox_seq=402)
    )

    assert await DjangoEsAppliedSeqReader().applied_seq("7") == 402


@pytest.mark.django_db(transaction=True)
async def test_the_watermark_stays_below_an_earlier_failed_search_projection():
    await record_es_pending_seq(7, 398, "failed-event")

    await AdvanceEsAppliedSeq(NotificationsAcknowledged).apply(
        make_event(NotificationsAcknowledged(user_id=7), outbox_seq=402)
    )

    assert await DjangoEsAppliedSeqReader().applied_seq("7") == 397

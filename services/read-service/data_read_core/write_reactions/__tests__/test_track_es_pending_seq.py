import pytest
from fakes import make_event
from kafka_consumer_py import EventMessage
from kafka_messages import WalletCreated

from data_read_core.shared.read_at_least import (
    DjangoEsAppliedSeqReader,
    EsPendingOutboxSeq,
    record_es_applied_seq,
)
from data_read_core.write_reactions import TrackEsPendingSeq


class _RecordingHandler:
    def __init__(self) -> None:
        self.handled: list[EventMessage] = []

    async def __call__(self, event: EventMessage) -> None:
        self.handled.append(event)


class _FailingHandler:
    async def __call__(self, event: EventMessage) -> None:
        raise RuntimeError("search projection failed")


def _wallet_created(outbox_seq: int | None) -> EventMessage:
    return make_event(WalletCreated(user_id=7, wallet_id="w-1"), outbox_seq=outbox_seq)


@pytest.mark.django_db(transaction=True)
async def test_failed_plan_holds_its_seq_and_reraises():
    with pytest.raises(RuntimeError):
        await TrackEsPendingSeq(_FailingHandler(), WalletCreated)(_wallet_created(55))

    assert await EsPendingOutboxSeq.objects.filter(user_id=7, outbox_seq=55).aexists()


@pytest.mark.django_db(transaction=True)
async def test_a_later_success_of_the_same_event_releases_the_hold():
    with pytest.raises(RuntimeError):
        await TrackEsPendingSeq(_FailingHandler(), WalletCreated)(_wallet_created(55))

    await TrackEsPendingSeq(_RecordingHandler(), WalletCreated)(_wallet_created(55))

    assert not await EsPendingOutboxSeq.objects.filter(user_id=7).aexists()


@pytest.mark.django_db(transaction=True)
async def test_missing_outbox_seq_is_never_held():
    with pytest.raises(RuntimeError):
        await TrackEsPendingSeq(_FailingHandler(), WalletCreated)(_wallet_created(None))

    assert not await EsPendingOutboxSeq.objects.aexists()


@pytest.mark.django_db(transaction=True)
async def test_later_events_cannot_carry_the_watermark_past_a_held_seq():
    with pytest.raises(RuntimeError):
        await TrackEsPendingSeq(_FailingHandler(), WalletCreated)(_wallet_created(55))
    await record_es_applied_seq(user_id=7, outbox_seq=60)

    assert await DjangoEsAppliedSeqReader().applied_seq("7") == 54


@pytest.mark.django_db(transaction=True)
async def test_watermark_returns_to_the_high_water_mark_once_released():
    with pytest.raises(RuntimeError):
        await TrackEsPendingSeq(_FailingHandler(), WalletCreated)(_wallet_created(55))
    await record_es_applied_seq(user_id=7, outbox_seq=60)

    await TrackEsPendingSeq(_RecordingHandler(), WalletCreated)(_wallet_created(55))

    assert await DjangoEsAppliedSeqReader().applied_seq("7") == 60

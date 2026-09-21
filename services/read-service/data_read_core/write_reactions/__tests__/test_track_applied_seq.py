from datetime import UTC, datetime

import pytest
from fakes import make_event
from google.protobuf.timestamp_pb2 import Timestamp
from kafka_consumer_py import Effect, EventMessage
from kafka_messages import WalletCreated, WalletDeleted

from data_read_core.shared.postgres_orm import WalletReadModel
from data_read_core.shared.read_at_least import DjangoAppliedSeqReader
from data_read_core.write_reactions import CreateWalletReadModel, TrackAppliedSeq


class _RecordingEffect(Effect):
    def __init__(self) -> None:
        self.applied: list[EventMessage] = []

    async def apply(self, event: EventMessage) -> None:
        self.applied.append(event)


def _now_timestamp() -> Timestamp:
    timestamp = Timestamp()
    timestamp.FromDatetime(datetime.now(UTC))
    return timestamp


@pytest.mark.django_db(transaction=True)
async def test_records_seq_and_runs_inner():
    inner = _RecordingEffect()
    effect = TrackAppliedSeq(inner, WalletDeleted)

    await effect.apply(make_event(WalletDeleted(user_id=7, wallet_id="w-1"), outbox_seq=55))

    assert len(inner.applied) == 1
    assert await DjangoAppliedSeqReader().applied_seq("7") == 55


@pytest.mark.django_db(transaction=True)
async def test_records_seq_even_when_inner_is_a_noop():
    inner = _RecordingEffect()
    effect = TrackAppliedSeq(inner, WalletDeleted)

    await effect.apply(make_event(WalletDeleted(user_id=7, wallet_id="missing"), outbox_seq=12))

    assert await DjangoAppliedSeqReader().applied_seq("7") == 12


@pytest.mark.django_db(transaction=True)
async def test_missing_outbox_seq_projects_without_recording():
    inner = _RecordingEffect()
    effect = TrackAppliedSeq(inner, WalletDeleted)

    await effect.apply(make_event(WalletDeleted(user_id=7, wallet_id="w-1"), outbox_seq=None))

    assert len(inner.applied) == 1
    assert await DjangoAppliedSeqReader().applied_seq("7") is None


@pytest.mark.django_db(transaction=True)
async def test_projection_and_seq_are_committed_together():
    effect = TrackAppliedSeq(CreateWalletReadModel(), WalletCreated)
    event = make_event(
        WalletCreated(
            wallet_id="11111111-1111-1111-1111-111111111111",
            user_id=7,
            title="Vacation",
            currency_code="USD",
            created_at=_now_timestamp(),
        ),
        outbox_seq=77,
    )

    await effect.apply(event)

    assert await WalletReadModel.objects.filter(id="11111111-1111-1111-1111-111111111111").aexists()
    assert await DjangoAppliedSeqReader().applied_seq("7") == 77

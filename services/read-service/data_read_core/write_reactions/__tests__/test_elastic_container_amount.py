from datetime import UTC, datetime

import pytest
from fakes import FakeElasticsearch, make_event
from google.protobuf.timestamp_pb2 import Timestamp
from kafka_messages import TransactionCreated, TransactionDeleted, TransactionUpdated

from data_read_core.shared.elasticsearch import GOALS_INDEX, WALLETS_INDEX
from data_read_core.shared.postgres_orm import MoneyContainers, TransactionReadModel
from data_read_core.write_reactions import (
    AdjustContainerAmountOnCreate,
    AdjustContainerAmountOnDelete,
    AdjustContainerAmountOnUpdate,
)
from data_read_core.write_reactions.transaction_reactions import elastic_container_amount

pytestmark = pytest.mark.django_db(transaction=True)

WALLET_ID = "11111111-1111-1111-1111-111111111111"
GOAL_ID = "22222222-2222-2222-2222-222222222222"
TX_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def _ts() -> Timestamp:
    timestamp = Timestamp()
    timestamp.FromDatetime(datetime(2026, 2, 1, tzinfo=UTC))
    return timestamp


@pytest.fixture
def elastic(monkeypatch) -> FakeElasticsearch:
    client = FakeElasticsearch()
    monkeypatch.setattr(elastic_container_amount, "get_elasticsearch", lambda: client)
    return client


def _deltas(client: FakeElasticsearch) -> list[float]:
    return [script["params"]["delta"] for _index, _id, script, _retries in client.scripted]


def _indices(client: FakeElasticsearch) -> list[str]:
    return [index for index, _id, _script, _retries in client.scripted]


async def _stored_transaction(container_id: str, kind: str) -> None:
    await TransactionReadModel.objects.acreate(
        id=TX_ID,
        wallet_id=container_id,
        container_kind=kind,
        user_id=7,
        amount="40.00",
        currency_code="USD",
        name="Groceries",
        occurred_at=datetime(2026, 2, 1, tzinfo=UTC),
        created_at=datetime(2026, 2, 1, tzinfo=UTC),
    )


def _created(amount: str, container_kind: str = "") -> object:
    return make_event(
        TransactionCreated(
            transaction_id=TX_ID,
            wallet_id=GOAL_ID if container_kind == MoneyContainers.GOAL else WALLET_ID,
            user_id=7,
            amount=amount,
            name="Groceries",
            container_kind=container_kind,
            created_at=_ts(),
        )
    )


async def test_creation_adds_the_amount(elastic):
    await AdjustContainerAmountOnCreate().apply(_created("40.00"))

    index, identifier, _script, retries = elastic.scripted[0]
    assert (index, identifier) == (WALLETS_INDEX, WALLET_ID)
    assert _deltas(elastic) == [40.0]
    assert retries == 3


async def test_a_created_goal_container_moves_the_goal_progress(elastic):
    await AdjustContainerAmountOnCreate().apply(_created("40.00", MoneyContainers.GOAL))

    index, identifier, script, _retries = elastic.scripted[0]
    assert (index, identifier) == (GOALS_INDEX, GOAL_ID)
    assert script["source"] == elastic_container_amount.GOAL_PROGRESS_ADJUSTMENT_SCRIPT


async def test_creation_compensates_by_reversing_the_amount(elastic):
    event = _created("40.00")

    await AdjustContainerAmountOnCreate().apply(event)
    await AdjustContainerAmountOnCreate().compensate(event)

    assert _deltas(elastic) == [40.0, -40.0]


async def test_deletion_subtracts_the_amount(elastic):
    await _stored_transaction(WALLET_ID, MoneyContainers.WALLET)
    event = make_event(
        TransactionDeleted(
            transaction_id=TX_ID,
            wallet_id=WALLET_ID,
            user_id=7,
            amount="40.00",
            deleted_at=_ts(),
        )
    )

    await AdjustContainerAmountOnDelete().apply(event)
    await AdjustContainerAmountOnDelete().compensate(event)

    assert _deltas(elastic) == [-40.0, 40.0]
    assert _indices(elastic) == [WALLETS_INDEX, WALLETS_INDEX]


async def test_update_applies_only_the_difference(elastic):
    await _stored_transaction(WALLET_ID, MoneyContainers.WALLET)
    event = make_event(
        TransactionUpdated(
            transaction_id=TX_ID,
            wallet_id=WALLET_ID,
            user_id=7,
            previous_amount="40.00",
            new_amount="55.00",
            updated_at=_ts(),
        )
    )

    await AdjustContainerAmountOnUpdate().apply(event)
    await AdjustContainerAmountOnUpdate().compensate(event)

    assert _deltas(elastic) == [15.0, -15.0]


async def test_an_updated_goal_container_is_read_back_from_the_stored_transaction(elastic):
    await _stored_transaction(GOAL_ID, MoneyContainers.GOAL)
    event = make_event(
        TransactionUpdated(
            transaction_id=TX_ID,
            wallet_id=GOAL_ID,
            user_id=7,
            previous_amount="40.00",
            new_amount="55.00",
            updated_at=_ts(),
        )
    )

    await AdjustContainerAmountOnUpdate().apply(event)

    assert _indices(elastic) == [GOALS_INDEX]


async def test_a_zero_delta_touches_nothing(elastic):
    await _stored_transaction(WALLET_ID, MoneyContainers.WALLET)
    event = make_event(
        TransactionUpdated(
            transaction_id=TX_ID,
            wallet_id=WALLET_ID,
            user_id=7,
            previous_amount="40.00",
            new_amount="40.00",
            updated_at=_ts(),
        )
    )

    await AdjustContainerAmountOnUpdate().apply(event)

    assert elastic.scripted == []


async def test_a_container_with_no_wallet_document_is_ignored(elastic):
    elastic.missing_ids.add(WALLET_ID)

    await AdjustContainerAmountOnCreate().apply(_created("40.00"))

    assert elastic.scripted == []


async def test_an_atomic_group_unwinds_the_delta_when_a_later_effect_fails(elastic):
    from kafka_consumer_py import Effect, SyncProcessGroup

    class ExplodingEffect(Effect):
        async def apply(self, event) -> None:
            raise RuntimeError("redis is down")

    group = SyncProcessGroup(
        [AdjustContainerAmountOnCreate(), ExplodingEffect()],
        atomic=True,
    )

    with pytest.raises(RuntimeError):
        await group.run(_created("40.00"))

    assert _deltas(elastic) == [40.0, -40.0]


async def test_the_balance_delta_waits_until_it_is_searchable(elastic):
    from data_read_core.shared.elasticsearch import SEARCHABLE_REFRESH

    await AdjustContainerAmountOnCreate().apply(_created("40.00"))

    assert elastic.refreshes == [SEARCHABLE_REFRESH]

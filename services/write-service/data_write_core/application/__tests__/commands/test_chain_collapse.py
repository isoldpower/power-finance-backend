from datetime import datetime
from uuid import UUID

import pytest

from data_write_core.application.commands.transactions.delete_transaction import (
    DeleteTransactionCommand,
    DeleteTransactionCommandHandler,
)
from data_write_core.domain.aggregates import TransactionAggregate

from ..queries.fakes import (
    FakeMoneyFlowRepository,
    FakeTransactionRepository,
    make_flow,
    make_transaction_entity,
)

CHAIN = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
WALLET = "11111111-1111-1111-1111-111111111111"
CANCELLED = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
SURVIVOR = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
THIRD_LEG = "dddddddd-dddd-dddd-dddd-dddddddddddd"
MOMENT = datetime(2026, 2, 1)


class FakeOutboxRepository:
    def __init__(self) -> None:
        self.entries: list = []

    async def get_latest_sequence(self) -> int:
        return 42

    async def append(self, entry) -> int:
        self.entries.append(entry)

        return 42


def _handler(transaction_repository, outbox_repository=None):
    flows = FakeMoneyFlowRepository(
        user_transactions=[
            make_flow(SURVIVOR, WALLET, "-10.00"),
            make_flow(THIRD_LEG, WALLET, "-10.00"),
        ]
    )

    return DeleteTransactionCommandHandler(
        transaction_repository=transaction_repository,
        money_flow_repository=flows,
        wallet_repository=object(),
        outbox_repository=outbox_repository or FakeOutboxRepository(),
        goal_repository=object(),
        container_repository=object(),
    )


def _cancelled_aggregate() -> TransactionAggregate:
    entity = make_transaction_entity(
        CANCELLED,
        WALLET,
        chain_id=CHAIN,
        deleted_at=MOMENT,
    )

    return TransactionAggregate(
        transaction_entity=entity, flows=[make_flow(CANCELLED, WALLET, "-10.00")]
    )


def _command() -> DeleteTransactionCommand:
    return DeleteTransactionCommand(
        transaction_id=UUID(CANCELLED),
        user_id=7,
        user_external_id="user_abc",
    )


async def test_a_chain_with_two_survivors_is_left_alone():
    repository = FakeTransactionRepository(
        [
            make_transaction_entity(SURVIVOR, WALLET, chain_id=CHAIN),
            make_transaction_entity(THIRD_LEG, WALLET, chain_id=CHAIN),
        ]
    )
    repository.chains[str(CHAIN)] = {"user_id": 7}
    handler = _handler(repository)

    await handler._collapse_chain_if_spent(_cancelled_aggregate(), _command(), MOMENT)

    assert str(CHAIN) in repository.chains
    assert (await repository.get_user_transaction_by_id(SURVIVOR, 7)).chain_id == CHAIN


@pytest.mark.django_db(transaction=True)
async def test_the_last_survivor_is_released_and_the_chain_goes():
    repository = FakeTransactionRepository(
        [make_transaction_entity(SURVIVOR, WALLET, chain_id=CHAIN)]
    )
    repository.chains[str(CHAIN)] = {"user_id": 7}
    outbox = FakeOutboxRepository()
    handler = _handler(repository, outbox)

    await handler._collapse_chain_if_spent(_cancelled_aggregate(), _command(), MOMENT)

    assert str(CHAIN) not in repository.chains
    assert (await repository.get_user_transaction_by_id(SURVIVOR, 7)).chain_id is None


@pytest.mark.django_db(transaction=True)
async def test_releasing_the_last_survivor_announces_its_empty_chain():
    repository = FakeTransactionRepository(
        [make_transaction_entity(SURVIVOR, WALLET, chain_id=CHAIN)]
    )
    repository.chains[str(CHAIN)] = {"user_id": 7}
    outbox = FakeOutboxRepository()
    handler = _handler(repository, outbox)

    await handler._collapse_chain_if_spent(_cancelled_aggregate(), _command(), MOMENT)

    assert len(outbox.entries) == 1
    payload = outbox.entries[0].payload
    assert payload["transaction_id"] == SURVIVOR
    assert payload["chain_id"] == ""
    assert payload["previous_amount"] == payload["new_amount"]


async def test_a_chain_whose_legs_are_all_cancelled_leaves_no_row_behind():
    repository = FakeTransactionRepository(
        [make_transaction_entity(SURVIVOR, WALLET, chain_id=CHAIN, deleted_at=MOMENT)]
    )
    repository.chains[str(CHAIN)] = {"user_id": 7}
    outbox = FakeOutboxRepository()
    handler = _handler(repository, outbox)

    await handler._collapse_chain_if_spent(_cancelled_aggregate(), _command(), MOMENT)

    assert str(CHAIN) not in repository.chains
    assert outbox.entries == []


async def test_an_unchained_transaction_collapses_nothing():
    repository = FakeTransactionRepository([make_transaction_entity(SURVIVOR, WALLET)])
    outbox = FakeOutboxRepository()
    handler = _handler(repository, outbox)
    aggregate = TransactionAggregate(
        transaction_entity=make_transaction_entity(CANCELLED, WALLET, deleted_at=MOMENT),
        flows=[make_flow(CANCELLED, WALLET, "-10.00")],
    )

    assert await handler._collapse_chain_if_spent(aggregate, _command(), MOMENT) is None
    assert outbox.entries == []


@pytest.mark.django_db(transaction=True)
async def test_cancelled_legs_release_the_chain_they_still_reference():
    repository = FakeTransactionRepository(
        [
            make_transaction_entity(SURVIVOR, WALLET, chain_id=CHAIN),
            make_transaction_entity(CANCELLED, WALLET, chain_id=CHAIN, deleted_at=MOMENT),
            make_transaction_entity(THIRD_LEG, WALLET, chain_id=CHAIN, deleted_at=MOMENT),
        ]
    )
    repository.chains[str(CHAIN)] = {"user_id": 7}
    handler = _handler(repository)

    await handler._collapse_chain_if_spent(_cancelled_aggregate(), _command(), MOMENT)

    assert str(CHAIN) not in repository.chains
    for transaction_id in (SURVIVOR, CANCELLED, THIRD_LEG):
        assert (await repository.get_user_transaction_by_id(transaction_id, 7)).chain_id is None

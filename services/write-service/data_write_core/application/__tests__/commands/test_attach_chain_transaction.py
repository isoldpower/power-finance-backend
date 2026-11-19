from datetime import datetime
from decimal import Decimal
from uuid import UUID

import pytest

from data_write_core.application.commands import (
    AttachChainTransactionCommand,
    AttachChainTransactionCommandHandler,
    BindChainTransactionCommand,
    BindChainTransactionCommandHandler,
    ChainExistingEntryCommand,
    CreateTransactionChainCommand,
    CreateTransactionChainCommandHandler,
    CreateTransactionCommand,
)
from data_write_core.domain.exceptions import (
    TransactionAlreadyCancelledError,
    TransactionAlreadyChainedError,
    TransactionChainCancelledError,
    TransactionChainDuplicateMemberError,
    TransactionChainNotFoundError,
    TransactionChainTooLongError,
)
from data_write_core.domain.services.config import ChainSettings
from data_write_core.domain.value_objects import (
    MoneyContainerKind,
    MoneyContainerRef,
    TransactionType,
)

from ..queries.fakes import (
    FakeMoneyFlowRepository,
    FakeTransactionRepository,
    make_flow,
    make_transaction_entity,
)

CHAIN = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
WALLET = "11111111-1111-1111-1111-111111111111"
OTHER_CHAIN = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
LOOSE_TRANSACTION = "ffffffff-ffff-ffff-ffff-ffffffffffff"
SECOND_LOOSE_TRANSACTION = "99999999-9999-9999-9999-999999999999"
EXPENSE_LEG = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
INCOME_LEG = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
ATTACHED_LEG = "dddddddd-dddd-dddd-dddd-dddddddddddd"
MOMENT = datetime(2026, 2, 1)


class RecordingCreateTransactionHandler:
    def __init__(self, transaction_repository: FakeTransactionRepository) -> None:
        self.received: list[CreateTransactionCommand] = []
        self._transaction_repository = transaction_repository

    async def handle(self, command: CreateTransactionCommand):
        self.received.append(command)
        await self._transaction_repository.create_transaction(
            make_transaction_entity(
                ATTACHED_LEG,
                str(command.wallet_id),
                chain_id=command.chain_id,
                created_at=datetime(2026, 3, 1),
            )
        )

        return object(), 77


class StubContainer:
    def as_reference(self) -> MoneyContainerRef:
        return MoneyContainerRef(
            id=UUID(WALLET),
            kind=MoneyContainerKind.WALLET,
            currency_code="USD",
            title="Main",
        )


def _chain_leg(transaction_id: str, deleted_at: datetime | None = None):
    return make_transaction_entity(
        transaction_id,
        WALLET,
        chain_id=CHAIN,
        deleted_at=deleted_at,
    )


class FakeOutboxRepository:
    def __init__(self) -> None:
        self.entries: list = []

    async def get_latest_sequence(self) -> int:
        return 42

    async def append(self, entry) -> int:
        self.entries.append(entry)

        return 42


def _flows() -> FakeMoneyFlowRepository:
    return FakeMoneyFlowRepository(
        user_transactions=[
            make_flow(EXPENSE_LEG, WALLET, "-10.00"),
            make_flow(INCOME_LEG, WALLET, "10.00"),
            make_flow(ATTACHED_LEG, WALLET, "-2.50"),
            make_flow(LOOSE_TRANSACTION, WALLET, "-4.00"),
            make_flow(SECOND_LOOSE_TRANSACTION, WALLET, "4.00"),
        ]
    )


async def load_stub_container(container_id, user_id):
    return StubContainer()


def _handler(
    transaction_repository: FakeTransactionRepository,
    outbox_repository: FakeOutboxRepository | None = None,
):
    create_handler = RecordingCreateTransactionHandler(transaction_repository)
    handler = AttachChainTransactionCommandHandler(
        transaction_repository=transaction_repository,
        money_flow_repository=_flows(),
        wallet_repository=object(),
        outbox_repository=outbox_repository or FakeOutboxRepository(),
        goal_repository=object(),
        container_repository=object(),
        create_transaction_handler=create_handler,
    )
    handler.load_container_aggregate = load_stub_container
    return handler, create_handler


def _bind_handler(
    transaction_repository: FakeTransactionRepository,
    outbox_repository: FakeOutboxRepository | None = None,
) -> BindChainTransactionCommandHandler:
    handler = BindChainTransactionCommandHandler(
        transaction_repository=transaction_repository,
        money_flow_repository=_flows(),
        wallet_repository=object(),
        outbox_repository=outbox_repository or FakeOutboxRepository(),
        goal_repository=object(),
        container_repository=object(),
    )
    handler.load_container_aggregate = load_stub_container
    return handler


def _command() -> AttachChainTransactionCommand:
    return AttachChainTransactionCommand(
        user_id=7,
        user_external_id="user_abc",
        chain_id=CHAIN,
        wallet_id=UUID(WALLET),
        amount=Decimal("2.50"),
        name="Transfer fee",
        transaction_type=TransactionType.EXPENSE,
    )


async def test_the_new_transaction_is_created_as_a_member_of_the_chain():
    repository = FakeTransactionRepository([_chain_leg(EXPENSE_LEG), _chain_leg(INCOME_LEG)])
    handler, create_handler = _handler(repository)

    chain, write_version = await handler.handle(_command())

    assert create_handler.received[0].chain_id == CHAIN
    assert create_handler.received[0].name == "Transfer fee"
    assert write_version == 77
    assert chain.chain_id == CHAIN
    assert [str(transaction.id) for transaction in chain.transactions] == [
        EXPENSE_LEG,
        INCOME_LEG,
        ATTACHED_LEG,
    ]


async def test_an_unknown_chain_is_not_found():
    handler, create_handler = _handler(FakeTransactionRepository([]))

    with pytest.raises(TransactionChainNotFoundError):
        await handler.handle(_command())

    assert create_handler.received == []


async def test_a_fully_cancelled_chain_takes_no_new_transactions():
    repository = FakeTransactionRepository(
        [_chain_leg(EXPENSE_LEG, deleted_at=MOMENT), _chain_leg(INCOME_LEG, deleted_at=MOMENT)]
    )
    handler, create_handler = _handler(repository)

    with pytest.raises(TransactionChainCancelledError):
        await handler.handle(_command())

    assert create_handler.received == []


async def test_a_chain_at_its_length_limit_rejects_another_member():
    full_chain = [
        _chain_leg(f"00000000-0000-0000-0000-{index:012d}")
        for index in range(ChainSettings.MAX_CHAIN_LENGTH)
    ]
    handler, create_handler = _handler(FakeTransactionRepository(full_chain))

    with pytest.raises(TransactionChainTooLongError):
        await handler.handle(_command())

    assert create_handler.received == []


def _bind_command(transaction_id: str) -> BindChainTransactionCommand:
    return BindChainTransactionCommand(
        user_id=7,
        user_external_id="user_abc",
        chain_id=CHAIN,
        transaction_id=UUID(transaction_id),
    )


@pytest.mark.django_db(transaction=True)
async def test_an_existing_transaction_is_bound_to_the_chain():
    repository = FakeTransactionRepository(
        [
            _chain_leg(EXPENSE_LEG),
            _chain_leg(INCOME_LEG),
            make_transaction_entity(LOOSE_TRANSACTION, WALLET, created_at=datetime(2026, 1, 5)),
        ]
    )
    outbox = FakeOutboxRepository()
    handler = _bind_handler(repository, outbox)

    chain, write_version = await handler.handle(_bind_command(LOOSE_TRANSACTION))

    assert write_version == 42
    assert (await repository.get_user_transaction_by_id(LOOSE_TRANSACTION, 7)).chain_id == CHAIN
    assert LOOSE_TRANSACTION in [str(transaction.id) for transaction in chain.transactions]
    assert len(outbox.entries) == 1
    payload = outbox.entries[0].payload
    assert payload["transaction_id"] == LOOSE_TRANSACTION
    assert payload["chain_id"] == str(CHAIN)
    assert payload["previous_amount"] == payload["new_amount"]


async def test_a_transaction_from_another_chain_cannot_be_bound():
    repository = FakeTransactionRepository(
        [
            _chain_leg(EXPENSE_LEG),
            make_transaction_entity(LOOSE_TRANSACTION, WALLET, chain_id=OTHER_CHAIN),
        ]
    )
    handler = _bind_handler(repository)

    with pytest.raises(TransactionAlreadyChainedError):
        await handler.handle(_bind_command(LOOSE_TRANSACTION))


async def test_a_cancelled_transaction_cannot_be_bound():
    repository = FakeTransactionRepository(
        [
            _chain_leg(EXPENSE_LEG),
            make_transaction_entity(LOOSE_TRANSACTION, WALLET, deleted_at=MOMENT),
        ]
    )
    handler = _bind_handler(repository)

    with pytest.raises(TransactionAlreadyCancelledError):
        await handler.handle(_bind_command(LOOSE_TRANSACTION))


def _chain_creator(
    repository: FakeTransactionRepository,
    outbox: FakeOutboxRepository,
) -> CreateTransactionChainCommandHandler:
    creator = CreateTransactionChainCommandHandler(
        transaction_repository=repository,
        money_flow_repository=_flows(),
        wallet_repository=object(),
        outbox_repository=outbox,
        goal_repository=object(),
        container_repository=object(),
    )
    creator.load_container_aggregate = load_stub_container
    return creator


@pytest.mark.django_db(transaction=True)
async def test_a_new_chain_can_be_made_of_existing_transactions():
    repository = FakeTransactionRepository(
        [
            make_transaction_entity(LOOSE_TRANSACTION, WALLET),
            make_transaction_entity(SECOND_LOOSE_TRANSACTION, WALLET),
        ]
    )
    outbox = FakeOutboxRepository()

    chain, _ = await _chain_creator(repository, outbox).handle(
        CreateTransactionChainCommand(
            user_id=7,
            user_external_id="user_abc",
            entries=[
                ChainExistingEntryCommand(
                    temporary_id="out", transaction_id=UUID(LOOSE_TRANSACTION)
                ),
                ChainExistingEntryCommand(
                    temporary_id="in",
                    transaction_id=UUID(SECOND_LOOSE_TRANSACTION),
                    after="out",
                ),
            ],
        )
    )

    for transaction_id in (LOOSE_TRANSACTION, SECOND_LOOSE_TRANSACTION):
        bound = await repository.get_user_transaction_by_id(transaction_id, 7)
        assert bound.chain_id == chain.chain_id
    assert str(chain.chain_id) in repository.chains
    assert [entry.payload["chain_id"] for entry in outbox.entries] == [str(chain.chain_id)] * 2
    assert {entry.event_type for entry in outbox.entries} == {"TransactionUpdated"}


async def test_a_transaction_referenced_twice_is_rejected():
    repository = FakeTransactionRepository([make_transaction_entity(LOOSE_TRANSACTION, WALLET)])

    with pytest.raises(TransactionChainDuplicateMemberError):
        await _chain_creator(repository, FakeOutboxRepository()).handle(
            CreateTransactionChainCommand(
                user_id=7,
                user_external_id="user_abc",
                entries=[
                    ChainExistingEntryCommand(
                        temporary_id="a", transaction_id=UUID(LOOSE_TRANSACTION)
                    ),
                    ChainExistingEntryCommand(
                        temporary_id="b", transaction_id=UUID(LOOSE_TRANSACTION)
                    ),
                ],
            )
        )

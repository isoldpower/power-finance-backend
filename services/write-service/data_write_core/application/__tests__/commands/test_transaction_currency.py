"""Where the currency on `TransactionCreated` comes from.

ai-service denominates every posting it writes from this one field, and it has
no other source for it: the ledger never sees the wallet. A transaction that
leaves here without its container's currency lands as an undenominated row.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from data_write_core.application.commands.transaction_chains.create_transaction_chain import (
    currency_of,
)
from data_write_core.application.commands.transactions.create_transaction import (
    transaction_created_entry,
)
from data_write_core.application.commands.transactions.transaction_factory import (
    build_transaction,
)
from data_write_core.application.dtos import MoneyContainerDTO
from data_write_core.domain.aggregates import TransactionAggregate
from data_write_core.domain.entities import TransactionEntity
from data_write_core.domain.value_objects import (
    MoneyContainerKind,
    MoneyContainerRef,
    TransactionMetadata,
)

EUR_WALLET = UUID("11111111-1111-1111-1111-111111111111")
JPY_WALLET = UUID("22222222-2222-2222-2222-222222222222")


def _aggregate(container_id: UUID, currency: str) -> TransactionAggregate:
    return build_transaction(
        user_id=7,
        container=MoneyContainerRef(
            id=container_id,
            kind=MoneyContainerKind.WALLET,
            currency_code=currency,
            title="Main",
        ),
        metadata=TransactionMetadata(name="Groceries"),
        amount=Decimal("125.00"),
        transaction_type=TransactionEntity.type_for(Decimal("-125.00")),
        created_at=datetime(2026, 1, 1),
    )


def _dto(container_id: UUID, currency: str) -> MoneyContainerDTO:
    return MoneyContainerDTO(
        id=container_id,
        name="Main",
        currency=currency,
        kind=MoneyContainerKind.WALLET,
    )


def test_the_created_event_carries_the_currency_it_is_given():
    entry = transaction_created_entry(
        _aggregate(EUR_WALLET, "EUR"),
        "user_abc",
        "EUR",
    )

    assert entry.payload["currency_code"] == "EUR"


def test_a_chained_transaction_takes_its_own_container_s_currency():
    """A transfer is one chain across two wallets. Reading the currency off the
    chain rather than off each transaction would denominate the far side of
    every cross-currency transfer wrongly."""

    containers = {
        str(EUR_WALLET): _dto(EUR_WALLET, "EUR"),
        str(JPY_WALLET): _dto(JPY_WALLET, "JPY"),
    }

    assert currency_of(_aggregate(EUR_WALLET, "EUR"), containers) == "EUR"
    assert currency_of(_aggregate(JPY_WALLET, "JPY"), containers) == "JPY"

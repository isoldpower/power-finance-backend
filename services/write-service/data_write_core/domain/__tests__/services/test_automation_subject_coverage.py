"""Every field a condition may name must be a field the matcher can see.

This is the silent failure the shared grammar exists to prevent, in its last
remaining form: adding a field to a policy without adding it to the subject
builder leaves a rule that VALIDATES when it is saved and never matches when it
runs. Nothing else in the system notices.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from filter_grammar_py import TRANSACTION_FILTER_POLICY, WALLET_FILTER_POLICY

from data_write_core.domain.aggregates import TransactionAggregate
from data_write_core.domain.entities import MoneyFlowEntity, TransactionEntity, WalletEntity
from data_write_core.domain.events import EventCollector
from data_write_core.domain.services import transaction_subject, wallet_subject
from data_write_core.domain.value_objects import (
    MoneyContainerKind,
    MoneyFlowData,
    TransactionMetadata,
    WalletData,
)

WALLET_ID = UUID("11111111-1111-1111-1111-111111111111")
TRANSACTION_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
CHAIN_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def fully_populated_transaction() -> TransactionAggregate:
    """Every optional field set: a subject built from a sparse transaction would
    hide a missing key behind an absent value."""

    transaction = TransactionEntity(
        id=TRANSACTION_ID,
        user_id="7",
        container_id=WALLET_ID,
        container_kind=MoneyContainerKind.WALLET,
        metadata=TransactionMetadata(
            name="Blue Bottle Coffee",
            category="Dining",
            evidence_url="https://example.com/receipt.png",
            chain_id=CHAIN_ID,
        ),
        created_at=datetime(2026, 9, 1, tzinfo=UTC),
        event_collector=EventCollector(),
    )
    flow = MoneyFlowEntity.from_persistence(
        id=uuid4(),
        user_id=7,
        created_at=datetime(2026, 9, 1, tzinfo=UTC),
        data=MoneyFlowData(
            transaction_id=TRANSACTION_ID,
            container_id=WALLET_ID,
            amount=Decimal("-4.50"),
        ),
    )

    return TransactionAggregate(transaction_entity=transaction, flows=[flow])


def test_the_transaction_subject_carries_every_filterable_transaction_field():
    subject = transaction_subject(fully_populated_transaction(), "USD")

    assert set(TRANSACTION_FILTER_POLICY) <= set(subject)


def test_the_wallet_subject_carries_every_filterable_wallet_field():
    wallet = WalletEntity.create(
        data=WalletData(title="Everyday", currency_code="USD"),
        id=str(WALLET_ID),
        user_id="7",
        created_at=datetime(2026, 9, 1, tzinfo=UTC),
        updated_at=datetime(2026, 9, 1, tzinfo=UTC),
    )

    subject = wallet_subject(wallet, Decimal("500.00"))

    assert set(WALLET_FILTER_POLICY) <= set(subject)

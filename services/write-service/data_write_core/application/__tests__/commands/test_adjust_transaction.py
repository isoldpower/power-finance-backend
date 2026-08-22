from datetime import datetime
from decimal import Decimal
from uuid import UUID

import pytest

from data_write_core.domain.aggregates import TransactionAggregate
from data_write_core.domain.entities import TransactionEntity
from data_write_core.domain.exceptions import (
    TransactionAlreadyCancelledError,
    TransactionDirectionChangeError,
)

from ..queries.fakes import make_flow, make_transaction_entity

TX_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
WALLET_ID = "11111111-1111-1111-1111-111111111111"


def _aggregate(*amounts: str, deleted_at: datetime | None = None) -> TransactionAggregate:
    return TransactionAggregate(
        transaction_entity=make_transaction_entity(TX_ID, WALLET_ID, deleted_at=deleted_at),
        flows=[
            make_flow(
                f"aaaaaaaa-aaaa-aaaa-aaaa-{index:012d}",
                WALLET_ID,
                amount,
                transaction_id=TX_ID,
            )
            for index, amount in enumerate(amounts)
        ],
    )


def _restate(aggregate: TransactionAggregate, magnitude: str):
    """What the view does: a positive magnitude, signed by the direction the
    transaction already has."""

    signed = TransactionEntity.signed(Decimal(magnitude), aggregate.type)

    return aggregate.adjust(signed)


def test_correcting_an_amount_keeps_the_original_flow():
    aggregate = _aggregate("-50.00")

    _restate(aggregate, "70.00")

    assert len(aggregate.flows) == 2
    assert aggregate.origin_flow.amount == Decimal("-50.00")
    assert aggregate.amount == Decimal("-70.00")


def test_the_appended_flow_is_the_difference_not_the_new_total():
    aggregate = _aggregate("-50.00")

    adjusting = _restate(aggregate, "70.00")

    assert adjusting.amount == Decimal("-20.00")
    assert adjusting.adjusts_other == UUID(aggregate.origin_flow.unique_id)


def test_correcting_downwards_appends_a_positive_delta():
    aggregate = _aggregate("-50.00")

    adjusting = _restate(aggregate, "30.00")

    assert adjusting.amount == Decimal("20.00")
    assert aggregate.amount == Decimal("-30.00")


def test_the_transaction_is_not_cancelled_by_a_correction():
    """The whole point of adjusting rather than cancel-and-recreate."""

    aggregate = _aggregate("-50.00")

    _restate(aggregate, "70.00")

    assert aggregate.root.deleted_at is None
    assert aggregate.is_cancelled is False
    assert str(aggregate.unique_id) == TX_ID


def test_the_wallet_sees_only_the_difference():
    aggregate = _aggregate("-50.00")

    _restate(aggregate, "70.00")

    assert aggregate.ledger_effect == Decimal("-70.00")


def test_corrections_compose():
    aggregate = _aggregate("-50.00")

    _restate(aggregate, "70.00")
    _restate(aggregate, "65.00")

    assert len(aggregate.flows) == 3
    assert aggregate.amount == Decimal("-65.00")


def test_restating_the_same_amount_appends_nothing():
    """Absolute semantics, so a replayed correction is naturally a no-op."""

    aggregate = _aggregate("-50.00")

    assert _restate(aggregate, "50.00") is None
    assert len(aggregate.flows) == 1


def test_an_income_stays_an_income():
    aggregate = _aggregate("40.00")

    _restate(aggregate, "90.00")

    assert aggregate.amount == Decimal("90.00")
    assert str(aggregate.type) == "income"


def test_the_direction_cannot_be_flipped_through_the_view_path():
    """The view signs the magnitude with the existing type, so a caller has no
    way to reach the flip — the domain guard is the backstop."""

    aggregate = _aggregate("-50.00")

    with pytest.raises(TransactionDirectionChangeError):
        aggregate.adjust(Decimal("30.00"))


def test_a_cancelled_transaction_cannot_be_corrected():
    aggregate = _aggregate("-50.00", deleted_at=datetime(2026, 2, 1))

    with pytest.raises(TransactionAlreadyCancelledError):
        _restate(aggregate, "70.00")

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import pytest

from data_write_core.domain.entities import TransactionEntity
from data_write_core.domain.events import EventCollector
from data_write_core.domain.exceptions import (
    TransactionAlreadyCancelledError,
    TransactionAlreadyChainedError,
    TransactionChainCancelledError,
    TransactionChainCycleError,
    TransactionChainDuplicateMemberError,
    TransactionChainTooLongError,
    TransactionChainUnknownReferenceError,
)
from data_write_core.domain.services import (
    ChainNode,
    bind_to_chain,
    ensure_chain_accepts_member,
    ensure_distinct_members,
    order_chain,
)
from data_write_core.domain.services.config import ChainSettings
from data_write_core.domain.value_objects import MoneyContainerKind, TransactionMetadata

ATTACH_CHAIN = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def _nodes(*pairs: tuple[str, str | None]) -> list[ChainNode]:
    return [ChainNode(temporary_id=temporary_id, after=after) for temporary_id, after in pairs]


def test_a_chain_with_no_dependencies_keeps_request_order():
    ordered = order_chain(_nodes(("a", None), ("b", None), ("c", None)))

    assert ordered == [0, 1, 2]


def test_a_dependency_commits_before_its_dependent():
    ordered = order_chain(_nodes(("second", "first"), ("first", None)))

    assert ordered == [1, 0]


def test_a_transfer_orders_the_expense_before_the_income():
    ordered = order_chain(_nodes(("transaction-1", None), ("transaction-2", "transaction-1")))

    assert ordered == [0, 1]


def test_a_chain_of_dependencies_resolves_transitively():
    ordered = order_chain(_nodes(("c", "b"), ("b", "a"), ("a", None)))

    assert ordered == [2, 1, 0]


def test_every_entry_appears_exactly_once():
    ordered = order_chain(_nodes(("a", None), ("b", "a"), ("c", "a")))

    assert sorted(ordered) == [0, 1, 2]


def test_a_cycle_is_rejected():
    with pytest.raises(TransactionChainCycleError):
        order_chain(_nodes(("a", "b"), ("b", "a")))


def test_a_self_reference_is_a_cycle():
    with pytest.raises(TransactionChainCycleError):
        order_chain(_nodes(("a", "a")))


def test_a_longer_cycle_is_rejected():
    with pytest.raises(TransactionChainCycleError):
        order_chain(_nodes(("a", "c"), ("b", "a"), ("c", "b")))


def test_an_unknown_reference_names_the_entry_that_made_it():
    with pytest.raises(TransactionChainUnknownReferenceError) as caught:
        order_chain(_nodes(("a", None), ("b", "nowhere")))

    assert caught.value.index == 1
    assert caught.value.reference == "nowhere"


def test_a_chain_at_the_cap_is_allowed():
    ordered = order_chain(
        _nodes(*((str(index), None) for index in range(ChainSettings.MAX_CHAIN_LENGTH)))
    )

    assert len(ordered) == ChainSettings.MAX_CHAIN_LENGTH


def test_a_chain_over_the_cap_is_rejected():
    with pytest.raises(TransactionChainTooLongError) as caught:
        order_chain(
            _nodes(*((str(index), None) for index in range(ChainSettings.MAX_CHAIN_LENGTH + 1)))
        )

    assert caught.value.maximum == ChainSettings.MAX_CHAIN_LENGTH


def _member(
    index: int,
    *,
    cancelled: bool = False,
    chain_id: UUID | None = ATTACH_CHAIN,
) -> TransactionEntity:
    return TransactionEntity(
        id=UUID(f"00000000-0000-0000-0000-{index:012d}"),
        user_id="7",
        container_id=UUID("11111111-1111-1111-1111-111111111111"),
        container_kind=MoneyContainerKind.WALLET,
        metadata=TransactionMetadata(name="Leg", chain_id=chain_id),
        created_at=datetime(2026, 1, 1),
        deleted_at=datetime(2026, 1, 2) if cancelled else None,
        event_collector=EventCollector(),
    )


def test_a_chain_with_a_live_member_accepts_another():
    ensure_chain_accepts_member(ATTACH_CHAIN, [_member(1, cancelled=True), _member(2)])


def test_a_chain_with_only_cancelled_members_accepts_nothing():
    with pytest.raises(TransactionChainCancelledError):
        ensure_chain_accepts_member(ATTACH_CHAIN, [_member(1, cancelled=True)])


def test_a_full_chain_accepts_nothing():
    full_chain = [_member(index) for index in range(ChainSettings.MAX_CHAIN_LENGTH)]

    with pytest.raises(TransactionChainTooLongError):
        ensure_chain_accepts_member(ATTACH_CHAIN, full_chain)


def test_a_loose_transaction_binds_to_the_chain():
    loose_transaction = _member(1, chain_id=None)

    bind_to_chain(loose_transaction, ATTACH_CHAIN, datetime(2026, 3, 1))

    assert loose_transaction.chain_id == ATTACH_CHAIN
    assert loose_transaction.updated_at == datetime(2026, 3, 1)


def test_a_chained_transaction_does_not_bind_again():
    with pytest.raises(TransactionAlreadyChainedError):
        bind_to_chain(_member(1), UUID(int=5), datetime(2026, 3, 1))


def test_a_cancelled_transaction_does_not_bind():
    with pytest.raises(TransactionAlreadyCancelledError):
        bind_to_chain(_member(1, cancelled=True, chain_id=None), ATTACH_CHAIN, datetime(2026, 3, 1))


def test_a_transaction_listed_twice_is_rejected():
    with pytest.raises(TransactionChainDuplicateMemberError):
        ensure_distinct_members([UUID(int=1), UUID(int=2), UUID(int=1)])

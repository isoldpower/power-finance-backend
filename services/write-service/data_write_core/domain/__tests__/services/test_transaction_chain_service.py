from __future__ import annotations

import pytest

from data_write_core.domain.exceptions import (
    TransactionChainCycleError,
    TransactionChainTooLongError,
    TransactionChainUnknownReferenceError,
)
from data_write_core.domain.services import MAX_CHAIN_LENGTH, ChainNode, order_chain


def _nodes(*pairs: tuple[str, str | None]) -> list[ChainNode]:
    return [ChainNode(temporary_id=temporary_id, after=after) for temporary_id, after in pairs]


def test_a_chain_with_no_dependencies_keeps_request_order():
    ordered = order_chain(_nodes(("a", None), ("b", None), ("c", None)))

    assert ordered == [0, 1, 2]


def test_a_dependency_commits_before_its_dependent():
    ordered = order_chain(_nodes(("second", "first"), ("first", None)))

    assert ordered == [1, 0]


def test_a_transfer_orders_the_expense_before_the_income():
    """The canonical case: two legs, the second stated as following the first."""

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
    ordered = order_chain(_nodes(*((str(index), None) for index in range(MAX_CHAIN_LENGTH))))

    assert len(ordered) == MAX_CHAIN_LENGTH


def test_a_chain_over_the_cap_is_rejected():
    with pytest.raises(TransactionChainTooLongError) as caught:
        order_chain(_nodes(*((str(index), None) for index in range(MAX_CHAIN_LENGTH + 1))))

    assert caught.value.maximum == MAX_CHAIN_LENGTH

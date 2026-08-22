from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from ..aggregates import TransactionAggregate
from ..entities import MoneyFlowEntity
from ..exceptions import (
    TransactionChainCycleError,
    TransactionChainTooLongError,
    TransactionChainUnknownReferenceError,
)

MAX_CHAIN_LENGTH = 100


@dataclass(frozen=True)
class ChainNode:
    temporary_id: str
    after: str | None


def order_chain(nodes: list[ChainNode]) -> list[int]:
    if len(nodes) > MAX_CHAIN_LENGTH:
        raise TransactionChainTooLongError(length=len(nodes), maximum=MAX_CHAIN_LENGTH)

    return _CommitOrderResolver(nodes).resolve()


class _CommitOrderResolver:
    def __init__(self, nodes: list[ChainNode]) -> None:
        self._nodes = nodes
        self._index_by_temporary_id = {node.temporary_id: index for index, node in enumerate(nodes)}
        self._ordered: list[int] = []
        self._placed: set[int] = set()
        self._visiting: set[int] = set()

    def resolve(self) -> list[int]:
        self._reject_unknown_references()
        for index in range(len(self._nodes)):
            self._place(index)

        return self._ordered

    def _reject_unknown_references(self) -> None:
        for index, node in enumerate(self._nodes):
            if node.after is not None and node.after not in self._index_by_temporary_id:
                raise TransactionChainUnknownReferenceError(index=index, reference=node.after)

    def _place(self, index: int) -> None:
        if index in self._placed:
            return
        if index in self._visiting:
            raise TransactionChainCycleError()

        self._visiting.add(index)
        dependency = self._nodes[index].after
        if dependency is not None:
            self._place(self._index_by_temporary_id[dependency])
        self._visiting.discard(index)

        self._placed.add(index)
        self._ordered.append(index)


@dataclass(frozen=True)
class CancelledTransaction:
    transaction: TransactionAggregate
    inverse_flow: MoneyFlowEntity
    outstanding_amount: Decimal


def cancel_chain(
    transactions: list[TransactionAggregate],
    cancelled_at: datetime,
) -> list[CancelledTransaction]:
    cancellations = []
    for transaction in transactions:
        outstanding_amount = transaction.amount
        inverse_flow = transaction.cancel(cancelled_at)
        if inverse_flow is None:
            continue

        cancellations.append(
            CancelledTransaction(
                transaction=transaction,
                inverse_flow=inverse_flow,
                outstanding_amount=outstanding_amount,
            )
        )

    return cancellations


def chain_flows(transactions: list[TransactionAggregate]) -> list[MoneyFlowEntity]:
    return [flow for transaction in transactions for flow in transaction.flows]

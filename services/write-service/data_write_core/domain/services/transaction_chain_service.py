from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from data_write_core.domain.services.config import ChainSettings

from ..aggregates import TransactionAggregate
from ..entities import MoneyFlowEntity, TransactionEntity
from ..exceptions import (
    TransactionAlreadyCancelledError,
    TransactionAlreadyChainedError,
    TransactionChainCancelledError,
    TransactionChainCycleError,
    TransactionChainDuplicateMemberError,
    TransactionChainTooLongError,
    TransactionChainUnknownReferenceError,
)


@dataclass(frozen=True)
class ChainNode:
    temporary_id: str
    after: str | None


def order_chain(nodes: list[ChainNode]) -> list[int]:
    if len(nodes) > ChainSettings.MAX_CHAIN_LENGTH:
        raise TransactionChainTooLongError(
            length=len(nodes), maximum=ChainSettings.MAX_CHAIN_LENGTH
        )

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


def ensure_chain_accepts_member(chain_id: UUID, members: list[TransactionEntity]) -> None:
    if not any(member.deleted_at is None for member in members):
        raise TransactionChainCancelledError(chain_id)

    grown_length = len(members) + 1
    if grown_length > ChainSettings.MAX_CHAIN_LENGTH:
        raise TransactionChainTooLongError(
            length=grown_length, maximum=ChainSettings.MAX_CHAIN_LENGTH
        )


def bind_to_chain(transaction: TransactionEntity, chain_id: UUID, now: datetime) -> None:
    transaction_id = UUID(transaction.unique_id)
    if transaction.deleted_at is not None:
        raise TransactionAlreadyCancelledError(transaction_id)
    if transaction.chain_id is not None:
        raise TransactionAlreadyChainedError(transaction_id, transaction.chain_id)

    transaction.join_chain(chain_id, now)


def ensure_distinct_members(transaction_ids: list[UUID]) -> None:
    seen_transaction_ids: set[UUID] = set()
    for transaction_id in transaction_ids:
        if transaction_id in seen_transaction_ids:
            raise TransactionChainDuplicateMemberError(transaction_id)
        seen_transaction_ids.add(transaction_id)

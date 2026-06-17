from decimal import Decimal
from uuid import UUID

from ..entities import TransactionEntity
from ..events import TransactionDeletedEvent
from ..exceptions import (
    CannotAdjustAdjustmentTransactionError,
    CannotCancelInverseTransactionError,
    TransactionAlreadyAdjustedError,
    TransactionAlreadyCancelledError,
)
from ..value_objects import TransactionData
from ._aggregate_root import AggregateRoot


class TransactionAggregate(AggregateRoot[TransactionEntity]):
    _cancelled_by: TransactionEntity | None
    _adjusted_by: TransactionEntity | None

    def __init__(
        self,
        transaction_entity: TransactionEntity,
        cancelled_by: TransactionEntity | None,
        adjusted_by: TransactionEntity | None,
    ):
        super().__init__(root=transaction_entity)

        self._cancelled_by = cancelled_by
        self._adjusted_by = adjusted_by

    def delete_self(self) -> "TransactionEntity":
        if self.root.cancels_other is not None:
            raise CannotCancelInverseTransactionError(transaction_id=UUID(self.unique_id))
        if self._cancelled_by is not None:
            raise TransactionAlreadyCancelledError(transaction_id=UUID(self.unique_id))

        inverse_transaction = self.root.create_inverse(event_collector=self.event_collector)
        self.event_collector.collect(
            TransactionDeletedEvent(
                transaction_id=UUID(self.unique_id),
                wallet_id=self.root.source_wallet_id,
                user_id=int(self.root.user_id),
                amount=self.root.amount,
                cancelled_by=UUID(inverse_transaction.unique_id),
                created_at=inverse_transaction.created_at,
            )
        )
        self._cancelled_by = inverse_transaction

        return inverse_transaction

    def adjust_self(self, new_amount: Decimal) -> "TransactionEntity":
        if self.root.adjusts_other is not None:
            raise CannotAdjustAdjustmentTransactionError(transaction_id=UUID(self.unique_id))
        if self._adjusted_by is not None:
            raise TransactionAlreadyAdjustedError(transaction_id=UUID(self.unique_id))
        if new_amount == self.root.amount:
            return self.root

        amount_delta = new_amount - self.root.amount
        adjust_transaction = TransactionEntity.create(
            user_id=int(self.root.user_id),
            data=TransactionData(
                amount=amount_delta,
                source_wallet_id=self.root.source_wallet_id,
                cancels_other=None,
                adjusts_other=UUID(self.root.unique_id),
            ),
            _event_collector=self.event_collector,
        )
        self._adjusted_by = adjust_transaction

        return adjust_transaction

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from ..entities import BalanceCheckpointEntity, TransactionEntity, WalletEntity
from ..events import WalletDeletedEvent, WalletUpdatedEvent
from ..exceptions import InvalidTransactionAmountError
from ..value_objects import TransactionData
from ._aggregate_root import AggregateRoot


class WalletAggregate(AggregateRoot[WalletEntity]):
    _checkpoint: BalanceCheckpointEntity | None
    _unsettled_transactions: list[TransactionEntity]

    def __init__(
        self,
        wallet_entity: WalletEntity,
        unsettled_transactions: list[TransactionEntity],
        balance_checkpoint: BalanceCheckpointEntity | None,
    ) -> None:
        super().__init__(root=wallet_entity)

        self._unsettled_transactions = list(unsettled_transactions)
        self._checkpoint = balance_checkpoint

    @property
    def balance(self) -> Decimal:
        base = self._checkpoint.balance if self._checkpoint else Decimal("0")
        unsettled = sum(
            (transaction.amount for transaction in self._unsettled_transactions),
            Decimal("0"),
        )
        return base + unsettled

    def apply_transaction(self, amount: Decimal) -> "TransactionEntity":
        if amount == Decimal("0"):
            raise InvalidTransactionAmountError(amount=amount)

        new_transaction = TransactionEntity.create(
            user_id=int(self.root.user_id),
            data=TransactionData(
                source_wallet_id=UUID(self.unique_id),
                amount=amount,
                cancels_other=None,
                adjusts_other=None,
            ),
            _event_collector=self.event_collector,
        )

        self._unsettled_transactions.append(new_transaction)
        return new_transaction

    def soft_delete(self, now: datetime) -> None:
        if self.root.deleted_at is not None:
            return

        self.root.mark_deleted(now)
        self.event_collector.collect(
            WalletDeletedEvent(
                wallet_id=UUID(self.unique_id),
                user_id=int(self.root.user_id),
                deleted_at=now,
            )
        )

    def rename(self, new_title: str, now: datetime) -> None:
        previous_title = self.root.title
        if new_title == previous_title:
            return

        self.root.rename(new_title=new_title, now=now)
        self.event_collector.collect(
            WalletUpdatedEvent(
                wallet_id=UUID(self.unique_id),
                user_id=int(self.root.user_id),
                previous_title=previous_title,
                new_title=new_title,
                updated_at=now,
            )
        )

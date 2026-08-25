from datetime import datetime
from decimal import Decimal
from uuid import UUID

from ..entities import BalanceCheckpointEntity, MoneyFlowEntity, WalletEntity
from ..entities.wallet import UNCHANGED
from ..events import WalletDeletedEvent, WalletUpdatedEvent
from ..exceptions import WalletClosedError, WalletNotEmptyError
from ..value_objects import MoneyContainerKind, MoneyContainerRef, WalletData
from ._aggregate_root import AggregateRoot


class WalletAggregate(AggregateRoot[WalletEntity]):
    _checkpoint: BalanceCheckpointEntity | None
    _unsettled_transactions: list[MoneyFlowEntity]

    def __init__(
        self,
        wallet_entity: WalletEntity,
        unsettled_transactions: list[MoneyFlowEntity],
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

    @property
    def currency_code(self) -> str:
        return self.root.currency_code

    @property
    def is_closed(self) -> bool:
        return self.root.deleted_at is not None

    def as_reference(self) -> MoneyContainerRef:
        return MoneyContainerRef(
            id=UUID(self.unique_id),
            kind=MoneyContainerKind.WALLET,
            currency_code=self.root.currency_code,
            title=self.root.title,
            is_closed=self.is_closed,
        )

    @property
    def owned(self) -> Decimal:
        return self.balance - self.root.zero_balance

    @property
    def is_empty(self) -> bool:
        return self.owned == Decimal("0")

    def record(self, flow: MoneyFlowEntity) -> None:
        if self.is_closed:
            raise WalletClosedError(UUID(self.unique_id))

        self._unsettled_transactions.append(flow)

    def soft_delete(self, now: datetime) -> None:
        if self.root.deleted_at is not None:
            return

        if not self.is_empty:
            raise WalletNotEmptyError(
                balance=self.balance,
                zero_balance=self.root.zero_balance,
            )

        self.root.mark_deleted(now)
        self.event_collector.collect(
            WalletDeletedEvent(
                wallet_id=UUID(self.unique_id),
                user_id=int(self.root.user_id),
                deleted_at=now,
            )
        )

    def rename(self, new_title: str, now: datetime) -> None:
        self.update_metadata(now=now, title=new_title)

    def replace(self, data: WalletData, now: datetime) -> None:
        self.update_metadata(
            now=now,
            title=data.title,
            category=data.category,
            color=data.color,
            favorite=data.favorite,
            zero_balance=data.zero_balance,
        )

    def update_metadata(
        self,
        now: datetime,
        title: str | object = UNCHANGED,
        category: str | object = UNCHANGED,
        color: str | object = UNCHANGED,
        favorite: bool | object = UNCHANGED,
        zero_balance: Decimal | object = UNCHANGED,
    ) -> None:
        previous_title = self.root.title
        changed = self.root.update_metadata(
            now=now,
            title=title,
            category=category,
            color=color,
            favorite=favorite,
            zero_balance=zero_balance,
        )
        if not changed:
            return

        self.event_collector.collect(
            WalletUpdatedEvent(
                wallet_id=UUID(self.unique_id),
                user_id=int(self.root.user_id),
                previous_title=previous_title,
                new_title=self.root.title,
                updated_at=now,
                category=self.root.category,
                color=self.root.color,
                favorite=self.root.favorite,
                zero_balance=self.root.zero_balance,
            )
        )

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional
from uuid import UUID
from datetime import datetime

from .balance_checkpoint import BalanceCheckpoint
from .transaction import Transaction
from ..events import EventCollector
from ..exceptions import InsufficientFundsException


@dataclass
class Wallet:
    id: UUID
    user_id: int
    name: str
    currency_code: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]
    unsettled_transactions: list[Transaction] = field(default_factory=list)
    checkpoint: Optional[BalanceCheckpoint] = field(default=None)

    _event_collector: EventCollector = field(default_factory=EventCollector)

    @classmethod
    def create(
            cls,
            user_id: int,
            name: str,
            currency_code: str,
            _event_collector: EventCollector | None = None,
    ):
        return cls(
            id=uuid.uuid4(),
            user_id=user_id,
            name=name,
            currency_code=currency_code,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            deleted_at=None,
            unsettled_transactions=[],
            checkpoint=None,
            _event_collector=_event_collector or EventCollector(),
        )

    @property
    def balance(self) -> Decimal:
        base = self.checkpoint.balance if self.checkpoint else Decimal('0')

        return base + sum((t.amount for t in self.unsettled_transactions), Decimal('0'))

    def _deposit_money(
            self,
            user_id: int,
            amount: Decimal,
    ) -> Transaction:
        if amount < Decimal('0'):
            raise InsufficientFundsException(abs(amount), self.balance)

        deposit_transaction = Transaction.create(
            user_id=user_id,
            amount=amount,
            source_wallet_id=self.id,
            event_collector=self._event_collector,
        )

        self.unsettled_transactions.append(deposit_transaction)
        return deposit_transaction

    def _withdraw_money(
            self,
            user_id: int,
            amount: Decimal,
    ) -> Transaction:
        new_balance = self.balance - amount
        if new_balance < Decimal('0'):
            raise InsufficientFundsException(abs(amount), self.balance)

        withdraw_transaction = Transaction.create(
            user_id=user_id,
            amount=amount,
            source_wallet_id=self.id,
            event_collector=self._event_collector,
        )

        self.unsettled_transactions.append(withdraw_transaction)
        return withdraw_transaction

    def apply_transaction(
            self,
            user_id: int,
            amount: Decimal,
    ) -> Transaction:
        if amount < Decimal('0'):
            return self._withdraw_money(user_id, abs(amount))
        elif amount > Decimal('0'):
            return self._deposit_money(user_id, abs(amount))
        else:
            raise AttributeError('Trying to add transaction with zero actual value')

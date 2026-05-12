import copy
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from django.utils import timezone

from .expense_category import ExpenseCategory
from .transaction_type import TransactionType
from ..events import (
    EventCollector,
    TransactionEventParticipant,
    TransactionCreatedEvent,
    TransactionUpdatedEvent,
    TransactionDeletedEvent,
    UpdateTransactionData,
)
from ..value_objects import Money


@dataclass
class TransactionParticipant:
    wallet_id: UUID
    money: Money


@dataclass
class _Transaction:
    """
    Transaction model represents any sort of money inflow/outflow transaction and is used to
    analyze money flows of the user.
    """

    id: UUID
    sender: TransactionParticipant | None
    receiver: TransactionParticipant | None
    description: str
    created_at: datetime
    type: TransactionType
    category: ExpenseCategory
    _event_collector: EventCollector = field(default_factory=EventCollector, compare=False)

    @classmethod
    def _validate_participants(
            cls,
            receiver: TransactionParticipant | None,
            sender: TransactionParticipant | None,
            type: TransactionType,
    ):
        if not sender and not receiver:
            raise ValueError('Transaction must have either sender or receiver. Got both undefined instead.')
        elif type == TransactionType.TRANSFER.value and not (sender and receiver):
            raise ValueError('Transaction with type set to TRANSFER should have both sender and receiver specified.')
        elif type == TransactionType.EXPENSE.value and not sender:
            raise ValueError('EXPENSE Transactions must have a sender specified.')
        elif type == TransactionType.INCOME.value and not receiver:
            raise ValueError('INCOME Transactions must have a receiver specified.')

    @classmethod
    def create(
            cls,
            sender: TransactionParticipant | None,
            receiver: TransactionParticipant | None,
            description: str,
            type: TransactionType,
            category: ExpenseCategory,
            event_collector: EventCollector | None = None,
    ):
        try:
            cls._validate_participants(receiver, sender, type)
        except ValueError as e:
            raise ValueError(f'Exception while creating new domain entity: {e}')

        created_transaction = cls(
            id=uuid4(),
            sender=TransactionParticipant(
                wallet_id=sender.wallet_id,
                money=sender.money,
            ) if sender else None,
            receiver=TransactionParticipant(
                wallet_id=receiver.wallet_id,
                money=receiver.money,
            ) if receiver else None,
            description=description,
            created_at=timezone.now(),
            type=type,
            category=category,
            _event_collector=event_collector or EventCollector(),
        )

        created_transaction._event_collector.collect(TransactionCreatedEvent(
            transaction_id=created_transaction.id,
            sender=TransactionEventParticipant(
                wallet_id=sender.wallet_id,
                amount=created_transaction.sender.money.amount,
                currency_code=created_transaction.sender.money.currency_code,
            ) if created_transaction.sender else None,
            receiver=TransactionEventParticipant(
                wallet_id=receiver.wallet_id,
                amount=created_transaction.receiver.money.amount,
                currency_code=created_transaction.receiver.money.currency_code,
            ) if created_transaction.receiver else None,
            description=created_transaction.description,
            created_at=created_transaction.created_at,
        ))

        return created_transaction

    @classmethod
    def from_persistence(
            cls,
            id: UUID,
            sender: TransactionParticipant | None,
            receiver: TransactionParticipant | None,
            description: str,
            type: TransactionType,
            category: ExpenseCategory,
            created_at: datetime,
            event_collector: EventCollector | None = None,
    ):
        try:
            cls._validate_participants(receiver, sender, type)
        except ValueError as e:
            raise ValueError(f'Exception while restoring domain entity Transaction from database: {e}')

        return cls(
            id=id,
            sender=sender,
            receiver=receiver,
            description=description,
            created_at=created_at,
            type=type,
            category=category,
            _event_collector=event_collector or EventCollector(),
        )

    def update_fields(
            self,
            category: ExpenseCategory | None = None,
            description: str | None = None,
    ):
        timestamp = timezone.now()
        old_transaction = copy.deepcopy(self)

        if category is not None:
            self.category = category
        if description is not None:
            self.description = description

        if old_transaction != self:
            self._event_collector.collect(TransactionUpdatedEvent(
                transaction_id=old_transaction.id,
                updated_at=timestamp,
                old_transaction=UpdateTransactionData(
                    sender=TransactionEventParticipant(
                        wallet_id=old_transaction.sender.wallet_id,
                        currency_code=old_transaction.sender.money.currency_code,
                        amount=old_transaction.sender.money.amount,
                    ) if old_transaction.sender else None,
                    receiver=TransactionEventParticipant(
                        wallet_id=old_transaction.receiver.wallet_id,
                        currency_code=old_transaction.receiver.money.currency_code,
                        amount=old_transaction.receiver.money.amount,
                    ) if old_transaction.receiver else None,
                    description=old_transaction.description,
                    category=old_transaction.category.value,
                ),
                current_transaction=UpdateTransactionData(
                    sender=self.sender,
                    receiver=self.receiver,
                    description=self.description,
                    category=self.category.value,
                )
            ))

    def migrate_event_collector(
            self,
            event_collector: EventCollector
    ):
        recorded_events = self._event_collector.pull_events()
        for event in recorded_events:
            event_collector.collect(event)

        self._event_collector = event_collector

    def confirm_delete(self):
        self._event_collector.collect(TransactionDeletedEvent(
            transaction_id=self.id,
            created_at=self.created_at,
            sender=self.sender,
            receiver=self.receiver,
            description=self.description
        ))

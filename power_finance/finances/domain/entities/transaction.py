from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from django.utils import timezone

from .expense_category import ExpenseCategory
from .transaction_type import TransactionType
from ..events import TransactionCreatedEvent, EventCollector, TransactionEventParticipant
from ..value_objects import Money


@dataclass
class TransactionParticipant:
    wallet_id: UUID
    money: Money


@dataclass
class Transaction:
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
    _event_collector: EventCollector = field(default_factory=EventCollector)

    @classmethod
    def _validate_participants(
            cls,
            receiver: TransactionParticipant | None,
            sender: TransactionParticipant | None,
            type: TransactionType,
    ):
        if not sender and not receiver:
            raise ValueError('Transaction must have either sender or receiver. Got both undefined instead.')
        elif type is TransactionType.TRANSFER and not (sender and receiver):
            raise ValueError('Transaction with type set to TRANSFER should have both sender and receiver specified.')
        elif type is TransactionType.EXPENSE and not sender:
            raise ValueError('EXPENSE Transactions must have a sender specified.')
        elif type is TransactionType.INCOME and not receiver:
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
            _event_collector=event_collector
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
    ):
        try:
            cls._validate_participants(receiver, sender, type)
        except ValueError as e:
            raise ValueError(f'Exception while restoring domain entity Transaction from database: {e}')

        return cls(
            id=id,
            sender=TransactionParticipant(
                wallet_id=sender.wallet_id,
                money=sender.money,
            ) if sender else None,
            receiver=TransactionParticipant(
                wallet_id=receiver.wallet_id,
                money=receiver.money,
            ) if receiver else None,
            description=description,
            created_at=created_at,
            type=type,
            category=category
        )
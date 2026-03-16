from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from django.utils import timezone

from .expense_category import ExpenseCategory
from .transaction_type import TransactionType


@dataclass
class TransactionParticipant:
    wallet_id: UUID
    amount: Decimal


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
    ):
        try:
            cls._validate_participants(receiver, sender, type)
        except ValueError as e:
            raise ValueError(f'Exception while creating new domain entity: {e}')

        return cls(
            id=uuid4(),
            sender=TransactionParticipant(
                wallet_id=sender.wallet_id,
                amount=sender.amount,
            ) if sender else None,
            receiver=TransactionParticipant(
                wallet_id=receiver.wallet_id,
                amount=receiver.amount,
            ) if receiver else None,
            description=description,
            created_at=timezone.now(),
            type=type,
            category=category
        )

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
                amount=sender.amount,
            ) if sender else None,
            receiver=TransactionParticipant(
                wallet_id=receiver.wallet_id,
                amount=receiver.amount,
            ) if receiver else None,
            description=description,
            created_at=created_at,
            type=type,
            category=category
        )
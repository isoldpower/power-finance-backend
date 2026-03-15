from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

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
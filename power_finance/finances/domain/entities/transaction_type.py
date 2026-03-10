from enum import Enum


class TransactionType(str, Enum):
    EXPENSE = "expense"
    INCOME = "income"
    ADJUSTMENT = "adjustment"
    TRANSFER = "transfer"
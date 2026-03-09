from django.db import models


class TransactionType(models.TextChoices):
    EXPENSE = "expense", "Expense",
    INCOME = 'income', 'Income',
    ADJUSTMENT = 'adjustment', 'Adjustment',
    TRANSFER = 'transfer', 'Transfer'


class ExpenseCategory(models.TextChoices):
     FOOD = 'food', 'Food',
     TRANSPORTATION = 'transportation', 'Transportation',
     ENTERTAINMENT = 'entertainment', 'Entertainment',
     SHOPPING = 'shopping', 'Shopping',
     OTHER = 'other', 'Other',
     HEALTH = 'health', 'Health',
     EDUCATION = 'education', 'Education',
     TRAVEL = 'travel', 'Travel',
     BILLS = 'bills', 'Bills'
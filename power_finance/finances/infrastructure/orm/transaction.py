from uuid import uuid4
from django.db import models
from django.utils import timezone

from .object_managers import IgnoreDeletedWallets
from .wallet import WalletModel

from finances.domain.entities.transaction_type import TransactionType
from finances.domain.entities.expense_category import ExpenseCategory


class TransactionTypeChoices(models.TextChoices):
    EXPENSE = TransactionType.EXPENSE.value, "Expense"
    INCOME = TransactionType.INCOME.value, "Income"
    ADJUSTMENT = TransactionType.ADJUSTMENT.value, "Adjustment"
    TRANSFER = TransactionType.TRANSFER.value, "Transfer"


class ExpenseCategoryChoices(models.TextChoices):
    FOOD = ExpenseCategory.FOOD.value, "Food"
    TRANSPORTATION = ExpenseCategory.TRANSPORTATION.value, "Transportation"
    ENTERTAINMENT = ExpenseCategory.ENTERTAINMENT.value, "Entertainment"
    SHOPPING = ExpenseCategory.SHOPPING.value, "Shopping"
    OTHER = ExpenseCategory.OTHER.value, "Other"
    HEALTH = ExpenseCategory.HEALTH.value, "Health"
    EDUCATION = ExpenseCategory.EDUCATION.value, "Education"
    TRAVEL = ExpenseCategory.TRAVEL.value, "Travel"
    BILLS = ExpenseCategory.BILLS.value, "Bills"


class TransactionModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False, unique=True)
    send_wallet = models.ForeignKey(
        WalletModel,
        on_delete=models.CASCADE,
        null=True,
        related_name="send_wallet"
    )
    send_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    receive_wallet = models.ForeignKey(
        WalletModel,
        on_delete=models.CASCADE,
        null=True,
        related_name="receive_wallet"
    )
    receive_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    type = models.CharField(choices=TransactionTypeChoices.choices)
    category = models.CharField(
        choices=ExpenseCategoryChoices.choices,
        default=ExpenseCategory.OTHER,
        null=False
    )

    objects = IgnoreDeletedWallets()

    class Meta:
        db_table = "finances_transactions"

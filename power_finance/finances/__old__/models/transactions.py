from django.db import models

from uuid import uuid4

from django.utils import timezone

from .enums import TransactionType, ExpenseCategory
from finances.models import Wallet, Money


class Transaction(models.Model):
    """
    Transaction model represents any sort of money inflow/outflow transaction and is used to
    analyze money flows of the user.
    """

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False, unique=True)
    from_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, null=True, related_name="from_wallet")
    from_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    to_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, null=True, related_name="to_wallet")
    to_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    type = models.CharField(choices=TransactionType, blank=True, null=True)
    category = models.CharField(choices=ExpenseCategory, default=ExpenseCategory.OTHER)

    @property
    def from_money(self):
        if self.from_amount and self.from_wallet:
            return Money(self.from_amount, self.from_wallet.currency)
        return None

    @property
    def to_money(self):
        if self.to_amount and self.to_wallet:
            return Money(self.to_amount, self.to_wallet.currency)
        return None

    @property
    def from_data(self):
        if not self.from_wallet:
            return None
        return {
            "wallet": self.from_wallet,
            "amount": self.from_amount,
        }

    @property
    def to_data(self):
        if not self.to_wallet:
            return None
        return {
            "wallet": self.to_wallet,
            "amount": self.to_amount,
        }

from uuid import uuid4

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from .money import Currency, Money
from ..services.managers import SoftDeleteManager


class Wallet(models.Model):
    """
    Represents a user's financial account that stores balance in a specific currency and can be
    whether credit or debit. Each user can have multiple wallets
    """

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=120)
    balance_amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)
    credit = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False, related_name='owner')

    objects = SoftDeleteManager()

    class Meta:
        app_label = 'finances'

    def delete(self, *args, **kwargs):
        self.deleted_at = timezone.now()
        self.save()

    @property
    def balance(self):
        return Money(self.balance_amount, self.currency)

    @balance.setter
    def balance(self, value: Money):
        self.balance_amount = value.amount
        self.currency = value.currency

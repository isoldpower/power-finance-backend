from django.db import models
from decimal import Decimal
from dataclasses import dataclass


class Currency(models.Model):
    """
    ISO 4217 currency definition.
    """

    code = models.CharField(max_length=3, primary_key=True, unique=True)
    name = models.CharField(max_length=64)
    numeric = models.CharField(max_length=3)
    digits = models.IntegerField()

    class Meta:
        ordering = ["code"]
        db_table = "currencies"


@dataclass(frozen=True)
class Money:
    """
    Money dataclass used to bind amount to currency.
    """

    amount: Decimal
    currency: Currency

    def __str__(self):
        return f"{self.amount} {self.currency}"

from django.db import models


class CurrencyReadModel(models.Model):
    """ISO-4217 reference data, seeded. `symbol` is presentation-only."""

    code = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=64)
    symbol = models.CharField(max_length=8)
    numeric = models.CharField(max_length=3)
    digits = models.IntegerField()

    class Meta:
        ordering = ["code"]
        db_table = "read_currencies"

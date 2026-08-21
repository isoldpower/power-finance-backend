from django.db import models


class CurrencyReadModel(models.Model):
    """ISO-4217 reference data, seeded."""

    code = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=64)
    numeric = models.CharField(max_length=3)
    digits = models.IntegerField()

    class Meta:
        ordering = ["code"]
        db_table = "read_currencies"

from django.db import models


class CurrencyModel(models.Model):
    code = models.CharField(max_length=3, primary_key=True, unique=True)
    name = models.CharField(max_length=64)
    numeric = models.CharField(max_length=3)
    digits = models.IntegerField()

    class Meta:
        ordering = ["code"]
        db_table = "finances_currencies"
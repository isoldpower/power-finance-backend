from enum import StrEnum

from django.db import models


class AccountGroups(StrEnum):
    ASSETS = "assets"
    LIABILITIES = "liabilities"
    EQUITY = "equity"


class AccountReadModel(models.Model):
    id = models.UUIDField(primary_key=True)
    user_id = models.BigIntegerField()

    group = models.CharField(max_length=16, blank=True, default="")
    name = models.CharField(max_length=120)
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "read_accounts"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "group", "name"],
                name="ra_identity",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user_id", "group", "name"],
                include=["balance"],
                name="ra_user_chart_idx",
            ),
        ]

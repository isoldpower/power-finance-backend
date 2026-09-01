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
    currency_code = models.CharField(max_length=8, blank=True, default="")

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
                fields=["user_id", "-created_at", "-id"],
                include=["group", "name", "balance", "currency_code"],
                name="ra_user_keyset_idx",
            ),
            # The chart's own order is `created_at DESC` (above). This one
            # serves the `group` filter and the `meta.groups` aggregate, both
            # of which read the group without touching the sort key.
            models.Index(
                fields=["user_id", "group"],
                include=["balance", "currency_code"],
                name="ra_user_chart_idx",
            ),
        ]

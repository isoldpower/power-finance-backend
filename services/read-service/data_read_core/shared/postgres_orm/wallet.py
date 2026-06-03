from django.db import models


class WalletReadModel(models.Model):
    """Denormalised wallet projection."""

    id = models.UUIDField(primary_key=True)
    user_id = models.BigIntegerField()
    title = models.CharField(max_length=255)
    currency_code = models.CharField(max_length=8)
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "read_wallets"
        indexes = [
            models.Index(
                fields=["user_id", "-created_at"],
                include=["title", "currency_code", "balance"],
                name="rw_user_created_idx",
            ),
            models.Index(
                fields=["user_id", "currency_code"],
                name="rw_user_currency_idx",
            ),
            models.Index(
                fields=["currency_code"],
                name="rw_currency_idx",
            ),
        ]

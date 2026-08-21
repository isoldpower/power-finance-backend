from django.db import models


class TransactionReadModel(models.Model):
    """Denormalized transaction projection."""

    id = models.UUIDField(primary_key=True)
    wallet_id = models.UUIDField()
    user_id = models.BigIntegerField()
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    currency_code = models.CharField(max_length=8, blank=True, default="")
    occurred_at = models.DateTimeField()
    created_at = models.DateTimeField()

    class Meta:
        db_table = "read_transactions"
        indexes = [
            models.Index(
                fields=["wallet_id", "-occurred_at"],
                include=["amount", "currency_code", "user_id"],
                name="rt_wallet_occurred_idx",
            ),
            models.Index(
                fields=["user_id", "-occurred_at"],
                include=["amount", "currency_code", "wallet_id"],
                name="rt_user_occurred_idx",
            ),
            models.Index(
                fields=["wallet_id", "-created_at"],
                name="rt_wallet_created_idx",
            ),
            models.Index(
                fields=["user_id", "currency_code"],
                name="rt_user_currency_idx",
            ),
            models.Index(
                fields=["user_id", "-created_at", "-id"],
                include=["amount", "currency_code", "wallet_id"],
                name="rt_user_keyset_idx",
            ),
        ]

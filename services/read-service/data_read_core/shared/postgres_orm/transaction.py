from enum import StrEnum
from uuid import UUID

from django.db import models

NO_CHAIN_SENTINEL = UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")


class MoneyContainers(StrEnum):
    WALLET = "wallet"
    GOAL = "goal"


class TransactionReadModel(models.Model):
    id = models.UUIDField(primary_key=True)
    wallet_id = models.UUIDField()
    wallet_name = models.CharField(max_length=255, blank=True, default="")
    container_kind = models.CharField(max_length=8, default=MoneyContainers.WALLET)
    user_id = models.BigIntegerField()
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    currency_code = models.CharField(max_length=8, blank=True, default="")

    name = models.CharField(max_length=255, blank=True, default="")
    category = models.CharField(max_length=255, blank=True, null=True)
    evidence_url = models.URLField(max_length=2048, blank=True, null=True)
    origin = models.CharField(max_length=16, blank=True, default="manual")
    chain_id = models.UUIDField(blank=True, null=True)
    chain_sort = models.UUIDField(default=NO_CHAIN_SENTINEL)

    occurred_at = models.DateTimeField()
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "read_transactions"
        indexes = [
            models.Index(
                fields=["user_id", "-created_at", "chain_sort", "-id"],
                include=["amount", "currency_code", "wallet_id", "wallet_name", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="rt_user_chain_keyset_idx",
            ),
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
                condition=models.Q(deleted_at__isnull=True),
                name="rt_wallet_created_idx",
            ),
            models.Index(
                fields=["user_id", "currency_code"],
                name="rt_user_currency_idx",
            ),
            models.Index(
                fields=["chain_id"],
                name="rt_chain_idx",
            ),
        ]

from uuid import uuid4

from django.contrib.auth.models import User
from django.db import models

from .money_container import MoneyContainerModel


class TransactionChainModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transaction_chains")
    created_at = models.DateTimeField()
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "finances_transaction_chains"
        indexes = [
            models.Index(
                fields=["user", "-created_at"],
                name="ftc_user_created_idx",
            )
        ]


class TransactionModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="transactions")
    container = models.ForeignKey(
        MoneyContainerModel,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    chain = models.ForeignKey(
        TransactionChainModel,
        on_delete=models.PROTECT,
        related_name="transactions",
        blank=True,
        null=True,
    )

    name = models.CharField(max_length=255)
    category = models.CharField(max_length=255, blank=True, null=True)
    evidence_url = models.URLField(max_length=2048, blank=True, null=True)
    origin = models.CharField(max_length=16, default="manual")

    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "finances_transactions"
        indexes = [
            models.Index(fields=["user", "-created_at", "-id"], name="ft_user_keyset_idx"),
            models.Index(fields=["container", "-created_at"], name="ft_container_created_idx"),
            models.Index(fields=["chain"], name="ft_chain_idx"),
        ]

from typing import ClassVar
from uuid import uuid4

from django.contrib.auth.models import User
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from .object_managers import SoftDeleteManager


class CategoryModel(models.Model):
    TRANSACTION = "transaction"
    WALLET = "wallet"
    KIND_CHOICES = ((TRANSACTION, "Transaction"), (WALLET, "Wallet"))
    category_kind: ClassVar[str] = ""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    kind = models.CharField(max_length=16, choices=KIND_CHOICES, editable=False)
    name = models.CharField(max_length=120)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="categories",
        blank=True,
        null=True,
    )
    is_global = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    objects = SoftDeleteManager()

    class Meta:
        db_table = "finances_categories"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(is_global=True, user__isnull=True)
                    | models.Q(is_global=False, user__isnull=False)
                ),
                name="fc_global_has_no_owner",
            ),
            models.UniqueConstraint(
                "user",
                "kind",
                Lower("name"),
                condition=models.Q(deleted_at__isnull=True, is_global=False),
                name="fc_user_kind_name_unique",
            ),
            models.UniqueConstraint(
                "kind",
                Lower("name"),
                condition=models.Q(is_global=True),
                name="fc_global_kind_name_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "kind", "name"], name="fc_user_kind_name_idx"),
        ]

    def save(self, *arguments, **keyword_arguments):
        if self.category_kind:
            self.kind = self.category_kind

        super().save(*arguments, **keyword_arguments)


class TransactionCategoryModel(CategoryModel):
    category_kind = CategoryModel.TRANSACTION
    category = models.OneToOneField(
        CategoryModel,
        on_delete=models.CASCADE,
        parent_link=True,
        primary_key=True,
        db_column="id",
        related_name="transaction_category",
    )

    objects = SoftDeleteManager()

    class Meta:
        db_table = "finances_transaction_categories"


class WalletCategoryModel(CategoryModel):
    category_kind = CategoryModel.WALLET
    category = models.OneToOneField(
        CategoryModel,
        on_delete=models.CASCADE,
        parent_link=True,
        primary_key=True,
        db_column="id",
        related_name="wallet_category",
    )

    objects = SoftDeleteManager()

    class Meta:
        db_table = "finances_wallet_categories"

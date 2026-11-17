from enum import StrEnum

from django.db import models


class CategoryKinds(StrEnum):
    TRANSACTION = "transaction"
    WALLET = "wallet"


class CategoryReadModel(models.Model):
    id = models.UUIDField(primary_key=True)
    user_id = models.BigIntegerField(null=True, blank=True)
    kind = models.CharField(max_length=16)
    name = models.CharField(max_length=120)
    is_global = models.BooleanField(default=False)

    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "read_categories"
        indexes = [
            models.Index(
                fields=["user_id", "kind", "-is_global", "name", "id"],
                condition=models.Q(deleted_at__isnull=True),
                name="rc_user_kind_listing_idx",
            ),
            models.Index(
                fields=["is_global", "kind", "name", "id"],
                condition=models.Q(is_global=True),
                name="rc_global_listing_idx",
            ),
        ]

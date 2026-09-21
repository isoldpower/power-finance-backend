from typing import ClassVar
from uuid import uuid4

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from .currency import CurrencyModel
from .object_managers import SoftDeleteManager


class MoneyContainerModel(models.Model):
    WALLET = "wallet"
    GOAL = "goal"
    KIND_CHOICES = ((WALLET, "Wallet"), (GOAL, "Goal"))
    container_kind: ClassVar[str] = ""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    kind = models.CharField(max_length=16, choices=KIND_CHOICES, editable=False)
    name = models.CharField(max_length=120)
    currency = models.ForeignKey(CurrencyModel, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="money_containers")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    objects = SoftDeleteManager()

    class Meta:
        db_table = "finances_money_containers"
        indexes = [
            models.Index(fields=["user", "-created_at", "-id"], name="fmc_user_keyset_idx"),
        ]

    def save(self, *arguments, **keyword_arguments):
        if self.container_kind:
            self.kind = self.container_kind

        super().save(*arguments, **keyword_arguments)

    def delete(self, *arguments, **keyword_arguments):
        self.deleted_at = self.updated_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])

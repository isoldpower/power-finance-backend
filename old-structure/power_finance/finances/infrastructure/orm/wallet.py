from uuid import uuid4

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from .currency import CurrencyModel
from .object_managers import SoftDeleteManager


class WalletModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=120)
    currency = models.ForeignKey(CurrencyModel, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False, related_name='owner')

    objects = SoftDeleteManager()

    class Meta:
        db_table = "finances_wallets"

    def delete(self, *args, **kwargs):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])

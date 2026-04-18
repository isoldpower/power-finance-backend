from uuid import uuid4
from django.db import models
from django.utils import timezone

from .object_managers import IgnoreDeletedWallets
from .wallet import WalletModel


# class TransactionModel(models.Model):
#     objects = IgnoreDeletedWallets()
#
#     id = models.UUIDField(primary_key=True, default=uuid4, editable=False, unique=True)
#     send_wallet = models.ForeignKey(
#         WalletModel,
#         on_delete=models.CASCADE,
#         null=True,
#         related_name="send_wallet"
#     )
#     send_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True)
#     receive_wallet = models.ForeignKey(
#         WalletModel,
#         on_delete=models.CASCADE,
#         null=True,
#         related_name="receive_wallet"
#     )
#     receive_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True)
#     description = models.TextField(blank=True, null=True)
#     created_at = models.DateTimeField(default=timezone.now)
#
#     class Meta:
#         db_table = "finances_transactions"

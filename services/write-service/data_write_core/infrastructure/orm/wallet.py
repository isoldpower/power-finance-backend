from django.db import models

from .money_container import MoneyContainerModel
from .object_managers import SoftDeleteManager


class WalletModel(MoneyContainerModel):
    container_kind = MoneyContainerModel.WALLET
    container = models.OneToOneField(
        MoneyContainerModel,
        on_delete=models.CASCADE,
        parent_link=True,
        primary_key=True,
        db_column="id",
        related_name="wallet",
    )

    category = models.CharField(max_length=120, blank=True, default="")
    color = models.CharField(max_length=9, blank=True, default="")
    favorite = models.BooleanField(default=False)
    zero_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    objects = SoftDeleteManager()

    class Meta:
        db_table = "finances_wallets"

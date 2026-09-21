from django.db import models

from .money_container import MoneyContainerModel
from .object_managers import SoftDeleteManager


class GoalModel(MoneyContainerModel):
    container_kind = MoneyContainerModel.GOAL
    container = models.OneToOneField(
        MoneyContainerModel,
        on_delete=models.CASCADE,
        parent_link=True,
        primary_key=True,
        db_column="id",
        related_name="goal",
    )
    target = models.DecimalField(max_digits=20, decimal_places=2)
    finish_at = models.DateTimeField(blank=True, null=True)
    url = models.URLField(max_length=2048, blank=True, null=True)

    objects = SoftDeleteManager()

    class Meta:
        db_table = "finances_goals"

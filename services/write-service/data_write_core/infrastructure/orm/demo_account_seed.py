from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class DemoAccountSeedModel(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="demo_account_seed",
    )
    completed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "demo_account_seeds"

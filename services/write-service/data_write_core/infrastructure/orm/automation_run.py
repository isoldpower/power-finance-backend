from uuid import uuid4

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from data_write_core.domain.automations import RUN_KEY_MAX_LENGTH


class AutomationRunModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    automation = models.ForeignKey(
        "data_write_core.AutomationModel",
        on_delete=models.CASCADE,
        related_name="runs_made",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="automation_runs",
    )
    run_key = models.CharField(max_length=RUN_KEY_MAX_LENGTH)
    ran_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "automation_runs"
        constraints = [
            models.UniqueConstraint(
                fields=["automation", "run_key"],
                name="automation_run_once_per_key",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "ran_at"], name="automation_run_user_idx"),
        ]

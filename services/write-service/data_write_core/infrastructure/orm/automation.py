from uuid import uuid4

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class AutomationModel(models.Model):
    """A user-authored rule: WHEN something matches, DO something."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user_external_id = models.CharField(max_length=64, blank=True, default="")

    name = models.CharField(max_length=120)
    icon = models.CharField(max_length=64, blank=True, default="")
    enabled = models.BooleanField(default=True)

    trigger_type = models.CharField(max_length=16)
    trigger_event = models.CharField(max_length=32, blank=True, default="")
    trigger_schedule = models.CharField(max_length=16, blank=True, default="")
    filter_body = models.JSONField(null=True, blank=True)

    effects = models.JSONField(default=list)

    last_run_at = models.DateTimeField(null=True, blank=True)
    runs = models.IntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="automations")

    class Meta:
        db_table = "automations"
        indexes = [
            models.Index(
                fields=["user", "created_at"],
                condition=models.Q(deleted_at__isnull=True, enabled=True),
                name="automation_live_idx",
            ),
            models.Index(
                fields=["user", "enabled"],
                name="automation_user_enabled_idx",
            ),
        ]

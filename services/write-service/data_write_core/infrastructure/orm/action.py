from uuid import uuid4

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class ActionModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user_external_id = models.CharField(max_length=64, blank=True, default="")

    source = models.CharField(max_length=16)
    kind = models.CharField(max_length=64)
    severity = models.CharField(max_length=16, default="info")
    severity_rank = models.IntegerField(default=1)
    status = models.CharField(max_length=16, default="pending")

    title = models.CharField(max_length=160)
    body = models.TextField(blank=True, default="")
    subject_type = models.CharField(max_length=32, blank=True, default="")
    subject_id = models.CharField(max_length=64, blank=True, default="")

    money_amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    money_currency = models.CharField(max_length=8, blank=True, default="")

    group_key = models.CharField(max_length=128, blank=True, default="")
    occurrences = models.IntegerField(default=1)
    last_seen_at = models.DateTimeField(default=timezone.now)

    expires_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_id = models.CharField(max_length=64, blank=True, default="")

    resolutions = models.JSONField(default=list)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="actions")

    class Meta:
        db_table = "actions"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "group_key"],
                condition=models.Q(status="pending") & ~models.Q(group_key=""),
                name="action_one_pending_per_group",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user", "status"],
                name="action_user_status_idx",
            ),
            models.Index(
                fields=["expires_at"],
                name="action_expiry_idx",
            ),
        ]

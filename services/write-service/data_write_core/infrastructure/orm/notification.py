from uuid import uuid4

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

SEVERITY_MAX_LENGTH = 16
SUBJECT_TYPE_MAX_LENGTH = 32


class NotificationModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    title = models.CharField(max_length=120)
    body = models.TextField()
    payload = models.JSONField(blank=True, null=True)

    severity = models.CharField(max_length=SEVERITY_MAX_LENGTH, default="info")
    subject_type = models.CharField(max_length=SUBJECT_TYPE_MAX_LENGTH, blank=True, default="")
    subject_id = models.CharField(max_length=64, blank=True, default="")

    acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    class Meta:
        db_table = "notifications"
        indexes = [
            models.Index(
                fields=["user", "acknowledged_at"],
                name="notif_user_ack_idx",
            ),
        ]

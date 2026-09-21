from uuid import uuid4

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from data_write_core.infrastructure.orm.config import NotificationSettings


class NotificationModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    title = models.CharField(max_length=120)
    body = models.TextField()
    payload = models.JSONField(blank=True, null=True)

    severity = models.CharField(max_length=NotificationSettings.SEVERITY_MAX_LENGTH, default="info")
    subject_type = models.CharField(
        max_length=NotificationSettings.SUBJECT_TYPE_MAX_LENGTH, blank=True, default=""
    )
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

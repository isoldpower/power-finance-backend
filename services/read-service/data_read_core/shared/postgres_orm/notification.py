from enum import StrEnum

from django.db import models


class Severity(StrEnum):
    SEVERITY_INFO = "info"
    SEVERITY_WARNING = "warning"
    SEVERITY_CRITICAL = "critical"


class NotificationReadModel(models.Model):
    id = models.UUIDField(primary_key=True)
    user_id = models.BigIntegerField()

    severity = models.CharField(max_length=16, default=Severity.SEVERITY_INFO)
    title = models.CharField(max_length=120)
    body = models.TextField()
    payload = models.JSONField(null=True, blank=True)

    subject_type = models.CharField(max_length=32, blank=True, default="")
    subject_id = models.CharField(max_length=64, blank=True, default="")

    acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "read_notifications"
        indexes = [
            models.Index(
                fields=["user_id", "-created_at", "-id"],
                include=["severity", "title", "acknowledged_at"],
                name="rn_user_keyset_idx",
            ),
            models.Index(
                fields=["user_id", "acknowledged_at"],
                name="rn_user_unread_idx",
            ),
            models.Index(
                fields=["user_id", "severity"],
                name="rn_user_severity_idx",
            ),
        ]

from enum import StrEnum

from django.db import models


class ActionSource(StrEnum):
    ASSISTANT = "assistant"
    SCHEDULER = "scheduler"


class ActionSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ActionStatus(StrEnum):
    PENDING = "pending"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


class ActionReadModel(models.Model):
    id = models.UUIDField(primary_key=True)
    user_id = models.BigIntegerField()

    source = models.CharField(max_length=16)
    kind = models.CharField(max_length=64)
    severity = models.CharField(max_length=16, default=ActionSeverity.INFO)
    severity_rank = models.IntegerField(default=1)
    status = models.CharField(max_length=16, default=ActionStatus.PENDING)

    title = models.CharField(max_length=160)
    body = models.TextField(blank=True, default="")

    subject_type = models.CharField(max_length=32, blank=True, default="")
    subject_id = models.CharField(max_length=64, blank=True, default="")

    money_amount = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    money_currency = models.CharField(max_length=8, blank=True, default="")

    group_key = models.CharField(max_length=128, blank=True, default="")
    occurrences = models.IntegerField(default=1)
    last_seen_at = models.DateTimeField()

    expires_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolutions = models.JSONField(default=list)

    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "read_actions"
        indexes = [
            models.Index(
                fields=["user_id", "status", "-severity_rank", "-created_at", "-id"],
                include=["kind", "title", "severity"],
                name="ra_queue_keyset_idx",
            ),
            models.Index(
                fields=["user_id", "source"],
                name="ra_user_source_idx",
            ),
        ]

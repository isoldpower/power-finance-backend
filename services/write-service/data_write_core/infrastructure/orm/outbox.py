from uuid import uuid4

from django.db import models
from django.utils import timezone


class OutboxEntryModel(models.Model):
    id = models.BigAutoField(primary_key=True)
    event_id = models.UUIDField(default=uuid4, editable=False, unique=True)
    aggregate_type = models.CharField(max_length=64, db_column="aggregatetype")
    aggregate_id = models.CharField(max_length=64, db_column="aggregateid")
    partition_key = models.CharField(max_length=64, db_column="partitionkey", default="")
    event_type = models.CharField(max_length=128, db_column="type")
    payload = models.JSONField()
    occurred_at = models.DateTimeField(default=timezone.now)
    traceparent = models.CharField(max_length=64, null=True, blank=True)
    tracestate = models.CharField(max_length=512, null=True, blank=True)
    baggage = models.CharField(max_length=1024, null=True, blank=True)

    class Meta:
        db_table = "outbox_events"
        indexes = [
            models.Index(fields=["aggregate_type", "aggregate_id"]),
        ]

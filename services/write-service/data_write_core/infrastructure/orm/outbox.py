from uuid import uuid4

from django.db import models
from django.utils import timezone


class OutboxEntryModel(models.Model):
    """Transactional outbox row. Written in the same DB transaction as
    business state. Debezium tails the Postgres WAL and forwards rows to
    Kafka via the Outbox Event Router SMT, so column names match the SMT's
    expected defaults (`aggregatetype`, `aggregateid`, `type`, `payload`)."""

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    aggregate_type = models.CharField(max_length=64, db_column="aggregatetype")
    aggregate_id = models.CharField(max_length=64, db_column="aggregateid")
    event_type = models.CharField(max_length=128, db_column="type")
    payload = models.JSONField()
    occurred_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "outbox_events"
        indexes = [
            models.Index(fields=["aggregate_type", "aggregate_id"]),
        ]
